import sqlite3
import math
import time
from contextlib import contextmanager
from config import (
    STARTING_BALANCE, STARTING_BANK, XP_PER_LEVEL_BASE, XP_SCALE_FACTOR,
    DEMAND_SHIFT_BUY, SUPPLY_SHIFT_BUY, DEMAND_SHIFT_SELL, SUPPLY_SHIFT_SELL,
    PRICE_CLAMP_LOW, PRICE_CLAMP_HIGH,
)

DB_PATH = "bunny_bot.db"


# ── Connection helper ──────────────────────────────────────────────────────────

@contextmanager
def get_db():
    """
    Yields a database connection with high-performance configuration.
    Includes extensive corruption-prevention parameters (busy retry, memory temp store).
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Enable SQLite's native busy retry handler (Wait up to 30s for lock release instead of crashing)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    
    # --- PHYSICAL SAFETY HARDENING ---
    conn.execute("PRAGMA cache_size=-2000")     # Uses 2MB RAM cache to limit direct disk read/write cycles
    conn.execute("PRAGMA temp_store=MEMORY")    # Keeps temporary storage inside RAM to prevent filesystem write corruptions
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema init & Migration Engine ─────────────────────────────────────────────

def init_db():
    # Set the persistent Write-Ahead Logging (WAL) mode ONCE on a single connection
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    try:
        # WAL mode optimizes write performance while reducing risk of full database file corruption
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA wal_autocheckpoint=1000") # Auto-saves WAL changes back to primary .db file safely
        
        # PHYSICAL SECURITY STRUCTURAL AUDIT: Diagnose existing database structure health on startup
        cursor = conn.execute("PRAGMA quick_check")
        result = cursor.fetchone()
        if result and result[0] != "ok":
            print(f"[FATAL DATABASE SECURITY ALERT] Physical file structure check failed: {result[0]}")
        else:
            print("[DATABASE INTEGRITY CHECK] Physical file structures are fully healthy and verified.")
            
        conn.commit()
    except Exception as e:
        print(f"[DATABASE INIT WARNING] WAL and security audit setup failed: {e}")
    finally:
        conn.close()

    with get_db() as db:
        # Users Table (Contains the accepted_terms security column)
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT    NOT NULL,
                wallet      INTEGER NOT NULL DEFAULT 0,
                bank        INTEGER NOT NULL DEFAULT 0,
                reputation  INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 1,
                xp          INTEGER NOT NULL DEFAULT 0,
                accepted_terms INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Automated Schema Migrator: Safely alter existing users table if column is missing!
        try:
            cursor = db.execute("PRAGMA table_info(users)")
            columns = [row["name"] for row in cursor.fetchall()]
            
            if "accepted_terms" not in columns:
                db.execute("ALTER TABLE users ADD COLUMN accepted_terms INTEGER NOT NULL DEFAULT 0")
                print("[DATABASE MIGRATION] Safely altered 'users' table to add 'accepted_terms' column.")
        except Exception as migration_err:
            print(f"[DATABASE MIGRATION WARNING] Failed column migration: {migration_err}")

        # Market
        db.execute("""
            CREATE TABLE IF NOT EXISTS market (
                item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                base_price  INTEGER NOT NULL,
                current_price REAL  NOT NULL,
                demand      REAL    NOT NULL DEFAULT 1.0,
                supply      REAL    NOT NULL DEFAULT 1.0
            )
        """)

        # Inventory
        db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id     INTEGER,
                item_name   TEXT,
                quantity    INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, item_name),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)

        # Daily
        db.execute("""
            CREATE TABLE IF NOT EXISTS daily (
                user_id     INTEGER PRIMARY KEY,
                last_claim  INTEGER NOT NULL DEFAULT 0,
                streak      INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)


# ── User Profile & Dynamic Integrity Management ─────────────────────────────────

def ensure_user(user_id: int, username: str = "Unknown User"):
    """
    Ensures that a user profile exists in the users table.
    If the user does not exist, a new profile is initialized.
    Exposed globally to satisfy queries inside active command cogs.
    """
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            db.execute(
                """INSERT OR IGNORE INTO users (user_id, username, wallet, bank)
                   VALUES (?, ?, ?, ?)""",
                (user_id, username, STARTING_BALANCE, STARTING_BANK),
            )


def get_user(user_id: int):
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def create_user(user_id: int, username: str):
    with get_db() as db:
        db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, wallet, bank)
               VALUES (?, ?, ?, ?)""",
            (user_id, username, STARTING_BALANCE, STARTING_BANK),
        )


def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    query = "UPDATE users SET " + ", ".join([f"{k}=?" for k in kwargs.keys()]) + " WHERE user_id=?"
    values = list(kwargs.values()) + [user_id]
    with get_db() as db:
        db.execute(query, values)


# ── Market ────────────────────────────────────────────────────────────────────

def get_market_items():
    with get_db() as db:
        return db.execute("SELECT * FROM market").fetchall()


def get_market_item(item_name: str):
    with get_db() as db:
        return db.execute("SELECT * FROM market WHERE name=?", (item_name,)).fetchone()


def add_market_item(name: str, base_price: int):
    with get_db() as db:
        db.execute(
            """INSERT OR IGNORE INTO market (name, base_price, current_price)
               VALUES (?, ?, ?)""",
            (name, base_price, float(base_price)),
        )


def update_market_price(item_name: str, change_pct: float, is_buy: bool):
    with get_db() as db:
        item = db.execute("SELECT * FROM market WHERE name=?", (item_name,)).fetchone()
        if not item:
            return
        
        # Calculate shifts
        old_price = item["current_price"]
        old_demand = item["demand"]
        old_supply = item["supply"]

        if is_buy:
            new_demand = old_demand + DEMAND_SHIFT_BUY
            new_supply = max(0.1, old_supply - SUPPLY_SHIFT_BUY)
        else:
            new_demand = max(0.1, old_demand - DEMAND_SHIFT_SELL)
            new_supply = old_supply + SUPPLY_SHIFT_SELL

        # Price update
        new_price = item["base_price"] * (new_demand / new_supply)
        new_price = max(item["base_price"] * PRICE_CLAMP_LOW, min(item["base_price"] * PRICE_CLAMP_HIGH, new_price))

        db.execute(
            """UPDATE market SET current_price=?, demand=?, supply=?
               WHERE name=?""",
            (new_price, new_demand, new_supply, item_name),
        )


# ── Inventory ─────────────────────────────────────────────────────────────────

def get_inventory(user_id: int):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM inventory WHERE user_id=? AND quantity > 0",
            (user_id,),
        ).fetchall()


def add_inventory_item(user_id: int, item_name: str, amount: int = 1):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not user:
            db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, wallet, bank) VALUES (?, ?, ?, ?)",
                (user_id, "Unknown User", STARTING_BALANCE, STARTING_BANK),
            )

        row = db.execute(
            "SELECT * FROM inventory WHERE user_id=? AND item_name=?",
            (user_id, item_name),
        ).fetchone()
        if not row:
            db.execute(
                "INSERT OR IGNORE INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
                (user_id, item_name, amount),
            )
        else:
            db.execute(
                "UPDATE inventory SET quantity=quantity+? WHERE user_id=? AND item_name=?",
                (amount, user_id, item_name),
            )


def remove_inventory_item(user_id: int, item_name: str, amount: int = 1):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM inventory WHERE user_id=? AND item_name=?",
            (user_id, item_name),
        ).fetchone()
        if row:
            new_qty = max(0, row["quantity"] - amount)
            db.execute(
                "UPDATE inventory SET quantity=? WHERE user_id=? AND item_name=?",
                (new_qty, user_id, item_name),
            )


# ── Daily ─────────────────────────────────────────────────────────────────────

def get_daily(user_id: int):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not user:
            db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, wallet, bank) VALUES (?, ?, ?, ?)",
                (user_id, "Unknown User", STARTING_BALANCE, STARTING_BANK),
            )

        row = db.execute("SELECT * FROM daily WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            db.execute(
                "INSERT OR IGNORE INTO daily (user_id) VALUES (?)", (user_id,)
            )
            return db.execute("SELECT * FROM daily WHERE user_id=?", (user_id,)).fetchone()
        return row


def update_daily(user_id: int, streak: int):
    now = int(time.time())
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not user:
            db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, wallet, bank) VALUES (?, ?, ?, ?)",
                (user_id, "Unknown User", STARTING_BALANCE, STARTING_BANK),
            )

        db.execute(
            "UPDATE daily SET last_claim=?, streak=? WHERE user_id=?",
            (now, streak, user_id),
        )


# ── Leaderboard ───────────────────────────────────────────────────────────────

def get_leaderboard(kind: str = "wealth", limit: int = 10):
    with get_db() as db:
        if kind == "wealth":
            return db.execute(
                """SELECT username, wallet+bank AS total, level
                   FROM users ORDER BY total DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        if kind == "level":
            return db.execute(
                "SELECT username, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        if kind == "reputation":
            return db.execute(
                "SELECT username, reputation, level FROM users ORDER BY reputation DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return []

