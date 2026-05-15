import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    bank_balance INTEGER DEFAULT 0,
                    bank_limit INTEGER DEFAULT 10000,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    prestige INTEGER DEFAULT 0,
                    job_id INTEGER,
                    job_exp INTEGER DEFAULT 0,
                    job_promotions INTEGER DEFAULT 0,
                    last_daily TEXT,
                    last_weekly TEXT,
                    last_work TEXT,
                    last_crime TEXT,
                    last_rob TEXT,
                    last_adventure TEXT,
                    active_pet INTEGER,
                    property_count INTEGER DEFAULT 0,
                    perk_slots INTEGER DEFAULT 3,
                    created_at TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    category TEXT,
                    base_value INTEGER,
                    current_value INTEGER,
                    rarity TEXT,
                    demand_score REAL DEFAULT 0,
                    supply_score REAL DEFAULT 0,
                    last_value_update TEXT,
                    enchantable INTEGER DEFAULT 0,
                    usable INTEGER DEFAULT 0,
                    equipable INTEGER DEFAULT 0,
                    craftable INTEGER DEFAULT 0,
                    craft_recipe TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_id INTEGER,
                    quantity INTEGER DEFAULT 1,
                    enchantments TEXT DEFAULT '[]',
                    equipped INTEGER DEFAULT 0,
                    acquired_at TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS market_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_id INTEGER,
                    item_id INTEGER,
                    quantity INTEGER,
                    price_per_unit INTEGER,
                    total_price INTEGER,
                    listed_at TEXT,
                    active INTEGER DEFAULT 1
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    base_salary INTEGER,
                    max_promotions INTEGER,
                    promotion_bonus INTEGER,
                    requirements TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS pets (
                    pet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    pet_type TEXT,
                    name TEXT,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    happiness INTEGER DEFAULT 100,
                    hunger INTEGER DEFAULT 100,
                    strength INTEGER DEFAULT 10,
                    defense INTEGER DEFAULT 10,
                    speed INTEGER DEFAULT 10,
                    intelligence INTEGER DEFAULT 10,
                    active INTEGER DEFAULT 0,
                    adventure_count INTEGER DEFAULT 0
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    property_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    property_type TEXT,
                    name TEXT,
                    level INTEGER DEFAULT 1,
                    value INTEGER,
                    income_per_hour INTEGER,
                    last_collection TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS enchantments (
                    enchantment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    effect_type TEXT,
                    effect_value REAL,
                    rarity TEXT,
                    applicable_categories TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_perks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    perk_id TEXT,
                    activated_at TEXT,
                    expires_at TEXT,
                    active INTEGER DEFAULT 1
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS perks_catalog (
                    perk_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    cost INTEGER,
                    duration_hours INTEGER,
                    effect_type TEXT,
                    effect_value REAL,
                    max_stack INTEGER DEFAULT 1
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS potions_catalog (
                    potion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    effect_type TEXT,
                    effect_value REAL,
                    duration_minutes INTEGER,
                    rarity TEXT,
                    buy_price INTEGER,
                    sell_price INTEGER
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_potions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    potion_id INTEGER,
                    quantity INTEGER DEFAULT 1,
                    brewed_at TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    transaction_type TEXT,
                    amount INTEGER,
                    description TEXT,
                    timestamp TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS cooldowns (
                    user_id INTEGER,
                    command_name TEXT,
                    used_at TEXT,
                    PRIMARY KEY (user_id, command_name)
                )
            """)

            await db.commit()
            await self._seed_data(db)

    async def _seed_data(self, db: aiosqlite.Connection):
        cursor = await db.execute("SELECT COUNT(*) FROM items")
        count = await cursor.fetchone()
        if count[0] == 0:
            items = [
                ("Wooden Sword", "A basic training sword.", "weapon", 100, 100, "common", 1, 0, 1, 0),
                ("Iron Sword", "A sturdy iron blade.", "weapon", 500, 500, "uncommon", 1, 0, 1, 0),
                ("Dragon Slayer", "Legendary sword of heroes.", "weapon", 5000, 5000, "legendary", 1, 0, 1, 0),
                ("Leather Armor", "Light protection.", "armor", 150, 150, "common", 1, 0, 1, 0),
                ("Steel Plate", "Heavy duty armor.", "armor", 800, 800, "uncommon", 1, 0, 1, 0),
                ("Mythic Robes", "Enchanted wizard robes.", "armor", 4000, 4000, "epic", 1, 0, 1, 0),
                ("Pickaxe", "For mining ore.", "tool", 200, 200, "common", 0, 0, 0, 0),
                ("Fishing Rod", "Catch fish easily.", "tool", 150, 150, "common", 0, 0, 0, 0),
                ("Iron Ore", "Raw metal material.", "material", 50, 50, "common", 0, 0, 0, 1),
                ("Gold Ore", "Precious metal.", "material", 200, 200, "uncommon", 0, 0, 0, 1),
                ("Diamond", "Extremely rare gem.", "material", 2000, 2000, "rare", 0, 0, 0, 1),
                ("Health Potion", "Restores health.", "consumable", 50, 50, "common", 0, 1, 0, 0),
                ("Bunny Cookie", "A tasty treat.", "consumable", 25, 25, "common", 0, 1, 0, 0),
                ("Golden Carrot", "Rare bunny delicacy.", "consumable", 300, 300, "rare", 0, 1, 0, 0),
                ("Ancient Coin", "A collectible relic.", "collectible", 1000, 1000, "rare", 0, 0, 0, 0),
                ("Crown Jewel", "The ultimate collectible.", "collectible", 10000, 10000, "legendary", 0, 0, 0, 0),
                ("Pet Food", "Nutritious pet meal.", "pet_item", 30, 30, "common", 0, 1, 0, 0),
                ("Training Treat", "Boosts pet stats.", "pet_item", 100, 100, "uncommon", 0, 1, 0, 0),
                ("Small House Deed", "Property ownership paper.", "property_deed", 5000, 5000, "uncommon", 0, 0, 0, 0),
                ("Castle Deed", "Majestic castle deed.", "property_deed", 50000, 50000, "legendary", 0, 0, 0, 0),
                ("Enchant Scroll", "Used for enchanting.", "enchantment_scroll", 250, 250, "uncommon", 0, 1, 0, 0),
            ]
            for item in items:
                await db.execute("""
                    INSERT INTO items (name, description, category, base_value, current_value, rarity, enchantable, usable, equipable, craftable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, item)

        cursor = await db.execute("SELECT COUNT(*) FROM jobs")
        count = await cursor.fetchone()
        if count[0] == 0:
            jobs = [
                ("Cashier", "Handle transactions.", 100, 3, 50, "{}"),
                ("Farmer", "Grow crops.", 120, 4, 60, "{}"),
                ("Miner", "Extract ore.", 150, 5, 75, '{"level": 5}'),
                ("Fisher", "Catch fish.", 130, 4, 65, "{}"),
                ("Hunter", "Track beasts.", 140, 4, 70, '{"level": 3}'),
                ("Chef", "Cook meals.", 160, 5, 80, "{}"),
                ("Blacksmith", "Forge weapons.", 200, 5, 100, '{"level": 10}'),
                ("Merchant", "Trade goods.", 180, 6, 90, '{"level": 8}'),
                ("Guard", "Protect the town.", 170, 4, 85, '{"level": 5}'),
                ("Wizard", "Cast spells.", 250, 5, 125, '{"level": 15}'),
                ("Thief", "Steal treasures.", 220, 4, 110, '{"level": 12}'),
                ("Banker", "Manage finances.", 300, 6, 150, '{"level": 20}'),
            ]
            for job in jobs:
                await db.execute("""
                    INSERT INTO jobs (name, description, base_salary, max_promotions, promotion_bonus, requirements)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, job)

        cursor = await db.execute("SELECT COUNT(*) FROM enchantments")
        count = await cursor.fetchone()
        if count[0] == 0:
            enchants = [
                ("Sharp", "+20% damage for weapons.", "damage", 0.2, "common", '["weapon"]'),
                ("Lucky", "+15% luck.", "luck", 0.15, "uncommon", '["weapon", "armor", "tool"]'),
                ("Wealthy", "+10% coin gain.", "income", 0.1, "rare", '["armor", "tool"]'),
                ("Swift", "+10% speed.", "speed", 0.1, "common", '["armor", "tool"]'),
                ("Sturdy", "+25% defense.", "defense", 0.25, "uncommon", '["armor"]'),
                ("Wise", "+20% XP gain.", "xp", 0.2, "rare", '["armor", "tool"]'),
            ]
            for e in enchants:
                await db.execute("""
                    INSERT INTO enchantments (name, description, effect_type, effect_value, rarity, applicable_categories)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, e)

        cursor = await db.execute("SELECT COUNT(*) FROM perks_catalog")
        count = await cursor.fetchone()
        if count[0] == 0:
            perks = [
                ("double_xp", "Double XP", "Earn 2x experience points.", 5000, 24, "xp", 2.0, 1),
                ("double_coin", "Double Coins", "Earn 2x Bunny-Coins.", 8000, 24, "income", 2.0, 1),
                ("lucky_roll", "Lucky Roll", "+25% gambling win chance.", 3000, 12, "luck", 0.25, 1),
                ("market_master", "Market Master", "No market tax.", 10000, 48, "tax", 0.0, 1),
                ("adventure_boost", "Adventure Boost", "Better adventure rewards.", 4000, 24, "adventure", 1.5, 1),
            ]
            for p in perks:
                await db.execute("""
                    INSERT INTO perks_catalog (perk_id, name, description, cost, duration_hours, effect_type, effect_value, max_stack)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, p)

        cursor = await db.execute("SELECT COUNT(*) FROM potions_catalog")
        count = await cursor.fetchone()
        if count[0] == 0:
            potions = [
                ("Health Potion", "Restores 50 HP in adventures.", "health", 50, 30, "common", 100, 50),
                ("Strength Potion", "+20 strength for 1 hour.", "strength", 20, 60, "uncommon", 500, 250),
                ("Luck Potion", "+15% luck for 2 hours.", "luck", 15, 120, "rare", 1000, 500),
                ("Wealth Potion", "+50% coin find for 1 hour.", "wealth", 0.5, 60, "epic", 2000, 1000),
                ("Speed Potion", "+30 speed for 30 min.", "speed", 30, 30, "uncommon", 750, 375),
            ]
            for p in potions:
                await db.execute("""
                    INSERT INTO potions_catalog (name, description, effect_type, effect_value, duration_minutes, rarity, buy_price, sell_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, p)

        await db.commit()

    async def get_user(self, user_id: int, username: str = None) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                now = datetime.now().isoformat()
                await db.execute("""
                    INSERT INTO users (user_id, username, created_at)
                    VALUES (?, ?, ?)
                """, (user_id, username or "Unknown", now))
                await db.commit()
                return await self.get_user(user_id, username)
            return dict(zip([c[0] for c in cursor.description], row))

    async def update_user(self, user_id: int, **kwargs):
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in kwargs.items():
                await db.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
            await db.commit()

    async def add_balance(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def add_bank(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET bank_balance = bank_balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def add_xp(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def get_inventory(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT i.*, it.name, it.category, it.rarity, it.current_value 
                FROM inventory i
                JOIN items it ON i.item_id = it.item_id
                WHERE i.user_id = ?
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(zip([c[0] for c in cursor.description], row)) for row in rows]

    async def add_item(self, user_id: int, item_id: int, quantity: int = 1, enchantments: str = "[]"):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ? AND enchantments = ?
            """, (user_id, item_id, enchantments))
            row = await cursor.fetchone()
            if row:
                await db.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (quantity, row[0]))
            else:
                now = datetime.now().isoformat()
                await db.execute("""
                    INSERT INTO inventory (user_id, item_id, quantity, enchantments, acquired_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, item_id, quantity, enchantments, now))
            await db.commit()

    async def remove_item(self, user_id: int, item_id: int, quantity: int = 1):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))
            row = await cursor.fetchone()
            if row:
                if row[1] <= quantity:
                    await db.execute("DELETE FROM inventory WHERE id = ?", (row[0],))
                else:
                    await db.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (quantity, row[0]))
                await db.commit()
                return True
            return False

    async def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
            row = await cursor.fetchone()
            if row:
                return dict(zip([c[0] for c in cursor.description], row))
            return None

    async def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM items WHERE LOWER(name) = LOWER(?)", (name,))
            row = await cursor.fetchone()
            if row:
                return dict(zip([c[0] for c in cursor.description], row))
            return None

    async def update_item_value(self, item_id: int, demand_delta: float = 0, supply_delta: float = 0):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT base_value, demand_score, supply_score FROM items WHERE item_id = ?", (item_id,))
            row = await cursor.fetchone()
            if not row:
                return
            base_value, demand, supply = row
            new_demand = max(0, demand + demand_delta)
            new_supply = max(0, supply + supply_delta)
            multiplier = 1 + (new_demand - new_supply) * 0.005
            multiplier = max(0.1, min(5.0, multiplier))
            new_value = int(base_value * multiplier)
            now = datetime.now().isoformat()
            await db.execute("""
                UPDATE items SET demand_score = ?, supply_score = ?, current_value = ?, last_value_update = ?
                WHERE item_id = ?
            """, (new_demand, new_supply, new_value, now, item_id))
            await db.commit()

    async def add_transaction(self, user_id: int, t_type: str, amount: int, description: str):
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute("""
                INSERT INTO transactions (user_id, transaction_type, amount, description, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, t_type, amount, description, now))
            await db.commit()

    async def check_cooldown(self, user_id: int, command: str, cooldown_seconds: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT used_at FROM cooldowns WHERE user_id = ? AND command_name = ?
            """, (user_id, command))
            row = await cursor.fetchone()
            if not row:
                return True
            last = datetime.fromisoformat(row[0])
            diff = (datetime.now() - last).total_seconds()
            return diff >= cooldown_seconds

    async def set_cooldown(self, user_id: int, command: str):
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute("""
                INSERT OR REPLACE INTO cooldowns (user_id, command_name, used_at)
                VALUES (?, ?, ?)
            """, (user_id, command, now))
            await db.commit()

    async def get_leaderboard(self, sort_by: str = "balance", limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            valid_cols = ["balance", "bank_balance", "level", "xp", "prestige"]
            if sort_by not in valid_cols:
                sort_by = "balance"
            cursor = await db.execute(f"""
                SELECT user_id, username, {sort_by} as score,
                       (balance + bank_balance) as net_worth,
                       level, prestige
                FROM users
                ORDER BY {sort_by} DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(zip([c[0] for c in cursor.description], row)) for row in rows]
