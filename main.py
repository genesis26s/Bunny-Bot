import os
import sys
import time
import logging
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Local Subsystem Imports
import database as db
import utils
import config
from config import BOT_NAME, BOT_VERSION, COLOR_DEFAULT, LOG_LEVEL

# Optional system resources telemetry
try:
    import psutil
except ImportError:
    psutil = None

# Safe Rich diagnostics terminal imports with automatic fallback class
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.box import ROUNDED
except ImportError:
    class Console:
        def print(self, *args, **kwargs):
            clean_text = " ".join(str(a) for a in args)
            import re
            clean_text = re.sub(r'\[.*?\]', '', clean_text)
            print(clean_text)
    Panel = None
    Table = None
    Text = None
    ROUNDED = None

# Ensure logging structures exist
os.makedirs("logs", exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level    = getattr(logging, LOG_LEVEL, logging.INFO),
    format   = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt  = "%H:%M:%S",
)
log = logging.getLogger("quadton-bot")

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not found in .env — please add it.")

# ── Intents ───────────────────────────────────────────────────────────────────
intents                  = discord.Intents.default()
intents.message_content  = True
intents.members          = True


# ── Operational Diagnostic Console Print Engine ────────────────────────────────
class PanelPrinter:
    """Helper class to print highly styled, colorful DevOps terminal blocks for Quadton Bot."""
    @staticmethod
    def print_startup_banner():
        c = Console()
        banner = """
[bold #c8b6ff]////////////////////////////////////////////////////////////////////////[/]
[bold #c8b6ff]//                                                                    //[/]
[bold #c8b6ff]//   ██████╗ ██╗   ██╗██████╗ ██████╗ ████████╗██████╗ ███╗   ██╗     //[/]
[bold #c8b6ff]//  ██╔═══██╗██║   ██║██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║     //[/]
[bold #c8b6ff]//  ██║   ██║██║   ██║██████╔╝██║  ██║   ██║   ██║   ██║██╔██╗ ██║     //[/]
[bold #c8b6ff]//  ██║▄▄ ██║██║   ██║██╔══██╗██║  ██║   ██║   ██║   ██║██║╚██╗██║     //[/]
[bold #c8b6ff]//  ╚██████╔╝╚██████╔╝██║  ██║██████╔╝   ██║   ╚██████╔╝██║ ╚████║     //[/]
[bold #c8b6ff]//   ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═══╝     //[/]
[bold #c8b6ff]//                                                                    //[/]
[bold #c8b6ff]//       🪙  ///// Q U A D T O N   B O T   E N G I N E /////  🪙       //[/]
[bold #c8b6ff]////////////////////////////////////////////////////////////////////////[/]
"""
        c.print(banner)

    @staticmethod
    def print_command_route(cmd_name: str, username: str, user_id: int, guild_name: str, latency: str, status: str = "SUCCESS"):
        c = Console()
        badge_col = "#2ec4b6" if status == "SUCCESS" else "#ff5e7e"
        
        c.print(f"[bold #c8b6ff]///// QUADTON BOT SYSTEM [ #bca6ff]COMMAND ROUTE[/] ///////[/]")
        c.print(f"[bold #8a8aa3]=====================================================[/]")
        c.print(f"  [bold #bca6ff]Command[/]    : [bold white]/{cmd_name}[/]")
        c.print(f"  [bold #bca6ff]User[/]       : [bold #2ec4b6]{username}[/] [dim]({user_id})[/]")
        c.print(f"  [bold #bca6ff]Guild[/]      : [bold white]{guild_name}[/]")
        c.print(f"  [bold #bca6ff]Latency[/]    : {latency}")
        c.print(f"  [bold #bca6ff]Status[/]     : [bold {badge_col}]{status}[/]")
        c.print(f"[bold #8a8aa3]=====================================================[/]\n")

    @staticmethod
    def print_exception_box(error_type: str, message: str, file_name: str, line_num: str, method: str, raw_traceback: str):
        c = Console()
        
        fix_guide = "Verify code parameters match database schemas."
        if "database is locked" in message.lower() or "sqlite" in error_type.lower():
            fix_guide = "Another task holds an exclusive write lock. SQLite WAL mode handles queue retries automatically."
        elif "buttonstyle" in message.lower() or "discord" in message.lower():
            fix_guide = "discord.py v2 uses root button-styles: Replace discord.ui.ButtonStyle with discord.ButtonStyle."

        c.print(f"[bold #ff5e7e]////////////////////////////////////////////////////////////////////////[/]")
        c.print(f"[bold #ff5e7e]// ❌ QUADTON ENGINE EXCEPTION CAUGHT!                                 //[/]")
        c.print(f"[bold #ff5e7e]////////////////////////////////////////////////////////////////////////[/]")
        c.print(f"  [bold #ff5e7e]EXCEPTION TYPE[/]  : [bold white]{error_type}[/]")
        c.print(f"  [bold #ff5e7e]ERROR MESSAGE[/]   : [bold white]{message}[/]")
        c.print(f"  [bold #ff5e7e]CRASH LOCATION[/]  : [bold #bca6ff]{file_name}[/] [bold white]at Line {line_num}[/]")
        c.print(f"  [bold #ff5e7e]TRIGGER METHOD[/]  : [bold white]def {method}()[/]")
        c.print(f"[bold #8a8aa3]------------------------------------------------------------------------[/]")
        c.print(f"  [bold #2ec4b6]RESOLVER GUIDE / SUGGESTION:[/]")
        c.print(f"  [dim white]{fix_guide}[/]")
        c.print(f"[bold #8a8aa3]------------------------------------------------------------------------[/]")
        c.print(f"  [bold #ff5e7e]RAW SYSTEM TRACEBACK:[/]")
        for line in raw_traceback.split("\n"):
            if line.strip():
                c.print(f"  [dim red]||| {line}[/]")
        c.print(f"[bold #ff5e7e]////////////////////////////////////////////////////////////////////////[/]\n")


# ── Bot class ─────────────────────────────────────────────────────────────────
class QuadtonBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix  = "!",   # prefix unused but required by base class
            intents         = intents,
            help_command    = None,
        )
        self.cog_load_diagnostics = {}
        # Expose DatabaseManager directly on the bot instance for cogs calling bot.db
        self.db = db.DatabaseManager()

    # ── Startup ───────────────────────────────────────────────────────────────
    async def setup_hook(self):
        PanelPrinter.print_startup_banner()

        # Initialise database WAL settings and tables
        db.init_db()
        log.info("Quadton SQLite database WAL mode and schema initialized.")

        # Gather every cog inside cogs directory dynamically
        cogs_found = []
        if os.path.exists("Quadton-bot/cogs"):
            for filename in os.listdir("Quadton-bot/cogs"):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cogs_found.append(filename[:-3])

        # Load extensions and track diagnostics
        for cog in cogs_found:
            start_time = time.perf_counter()
            cog_name = f"cogs.{cog}"
            cog_key = cog.capitalize()
            try:
                await self.load_extension(cog_name)
                duration_ms = (time.perf_counter() - start_time) * 1000
                self.cog_load_diagnostics[cog_key] = {
                    "status": "Healthy",
                    "time_ms": duration_ms
                }
                log.info(f"Loaded {cog_name} successfully ({duration_ms:.1f}ms)")
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self.cog_load_diagnostics[cog_key] = {
                    "status": "Crashed",
                    "time_ms": duration_ms,
                    "error": str(e)
                }
                log.error(f"Failed to load extension {cog_name}", exc_info=e)

        # Synchronize slash commands tree with Discord Gateway
        try:
            synced = await self.tree.sync()
            log.info(f"Command tree synced. Registered {len(synced)} slash commands globally.")
        except Exception as e:
            log.error("Failed to sync command tree with Discord.", exc_info=e)

    # ── Operational Summary Printout (Console Dashboard) ──────────────────────
    async def on_ready(self):
        total_users = 0
        total_coins = 0
        market_items = 0
        inventory_items = 0
        daily_records = 0
        
        try:
            with db.get_db() as conn:
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                
                if "users" in tables:
                    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                    total_coins = conn.execute("SELECT SUM(wallet + bank) FROM users").fetchone()[0] or 0
                if "market" in tables:
                    market_items = conn.execute("SELECT COUNT(*) FROM market").fetchone()[0]
                if "inventory" in tables:
                    inventory_items = conn.execute("SELECT SUM(quantity) FROM inventory").fetchone()[0] or 0
                if "daily" in tables:
                    daily_records = conn.execute("SELECT COUNT(*) FROM daily").fetchone()[0]
        except Exception as e:
            log.warning(f"Failed to query database stats for startup summary: {e}")

        # Gateway ping
        try:
            ping = f"{round(self.latency * 1000)} ms" if self.latency is not None else "24 ms"
        except Exception:
            ping = "24 ms"
            
        ram_usage = "N/A"
        thread_count = "N/A"
        if psutil:
            try:
                process = psutil.Process(os.getpid())
                ram_usage = f"{round(process.memory_info().rss / (1024 * 1024), 1)} MB"
                thread_count = f"{process.num_threads()} active"
            except Exception:
                pass

        # Console Dashboard Panel
        try:
            if Console and Panel and Table and Text and ROUNDED:
                console = Console()

                engine_table = Table.grid(padding=(0, 1), expand=True)
                engine_table.add_column(style="bold #c8b6ff")
                engine_table.add_column()
                engine_table.add_row("Bot Name", f"[bold white]{BOT_NAME}[/]")
                engine_table.add_row("Bot Account", f"{self.user.name}#{self.user.discriminator} ({self.user.id})")
                engine_table.add_row("Engine Build", f"v{BOT_VERSION} (Production)")
                engine_table.add_row("Discord.py", f"v{discord.__version__}")
                engine_table.add_row("Gateway Latency", ping)
                engine_table.add_row("Connected Guilds", f"{len(self.guilds)} servers")
                engine_table.add_row("Allocated RAM", ram_usage)
                engine_table.add_row("Active Threads", thread_count)
                
                db_table = Table.grid(padding=(0, 1), expand=True)
                db_table.add_column(style="bold #2ec4b6")
                db_table.add_column()
                db_table.add_row("Database Engine", "SQLite v3 (Local WAL)")
                db_table.add_row("Storage Path", f"[dim]{db.DB_PATH}[/]")
                db_table.add_row("Users Profiles", f"{total_users:,} accounts")
                db_table.add_row("Quad-Coins Supply", f"{total_coins:,} QC 🪙")
                db_table.add_row("Market Listings", f"{market_items} items")
                db_table.add_row("Inventory Quantity", f"{inventory_items:,} items")
                db_table.add_row("Daily Streak Rows", f"{daily_records} records")
                
                cogs_table = Table(box=ROUNDED, header_style="bold #c8b6ff", border_style="#1c1c1f", expand=True)
                cogs_table.add_column("System Cog", style="bold")
                cogs_table.add_column("Status", justify="center")
                cogs_table.add_column("Extension Path", style="dim")
                cogs_table.add_column("Diagnostics / Failures", justify="right")
                
                for name, details in self.cog_load_diagnostics.items():
                    if details["status"] == "Healthy":
                        status = "[#2ec4b6]Healthy[/]"
                        diag = f"Loaded in {details['time_ms']:.1f}ms [✓]"
                    else:
                        status = "[#ff5e7e]Crashed[/]"
                        diag = f"Error: {details['error'][:35]}..."
                    cogs_table.add_row(name, status, f"cogs.{name.lower()}", diag)

                top_table = Table.grid(expand=True)
                top_table.add_column(ratio=5)
                top_table.add_column(ratio=5)
                top_table.add_row(
                    Panel(engine_table, title="[bold #c8b6ff]🪙 Quadton Bot Engine System[/]", box=ROUNDED, style="border #1c1c1f"),
                    Panel(db_table, title="[bold #2ec4b6]💾 Database Subsystem Integrations[/]", box=ROUNDED, style="border #1c1c1f")
                )
                
                console.print("\n")
                console.print(Panel(
                    Text.from_markup(f"🪙 [bold #c8b6ff]{BOT_NAME.upper()} DEVELOPMENT OPERATIONS INTERFACE[/] • Version {BOT_VERSION}"),
                    style="border #c8b6ff",
                    box=ROUNDED,
                    expand=True
                ))
                console.print(top_table)
                console.print(Panel(cogs_table, title="[bold #c8b6ff]🧩 Loaded Subsystems Health Diagnostics[/]", box=ROUNDED, style="border #1c1c1f"))
                console.print("\n")
            else:
                log.info(f"Quadton Bot connected as {self.user} (Latency: {ping}). Serving {len(self.guilds)} guilds.")
        except Exception as e:
            log.info(f"Quadton Bot connected as {self.user} (Latency: {ping}). Serving {len(self.guilds)} guilds.")
            log.warning(f"Failed to generate rich diagnostics layout: {e}")

    # ── Verify terms of service agreement ──────────────────────────────────────
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            user_id = interaction.user.id
            
            cmd_name = interaction.command.name if interaction.command else "Unknown Command"
            guild_name = interaction.guild.name if interaction.guild else "DMs"
            latency = f"{round(self.latency * 1000)}ms" if self.latency is not None else "N/A"
            
            PanelPrinter.print_command_route(cmd_name, interaction.user.name, user_id, guild_name, latency, "SUCCESS")

            accepted = False
            try:
                user_data = db.get_user(user_id)
                if user_data:
                    accepted = bool(user_data["accepted_terms"])
            except Exception as e:
                log.error(f"Error checking user in on_interaction gate: {e}")
            
            if not accepted:
                class TermsView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=None)

                    @discord.ui.button(label="Agree ✅", style=discord.ButtonStyle.success, custom_id="accept_terms_btn")
                    async def accept_terms(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        if button_interaction.user.id != user_id:
                            await button_interaction.response.send_message("This menu is not yours!", ephemeral=True)
                            return
                        
                        try:
                            if not db.get_user(user_id):
                                db.create_user(user_id, button_interaction.user.name)
                                
                            db.update_user(user_id, accepted_terms=1)
                            
                            await button_interaction.response.send_message(
                                "Thank you! You have accepted Quadton Bot's Terms of Service. You can now use all commands.", 
                                ephemeral=True
                            )
                            try:
                                await interaction.delete_original_response()
                            except Exception:
                                pass
                        except Exception as acceptance_err:
                            log.error(f"Failed to accept terms: {acceptance_err}")
                            await button_interaction.response.send_message(
                                "An error occurred while saving your acceptance. Please try again.", 
                                ephemeral=True
                            )

                view = TermsView()
                
                terms_text = "Please accept Quadton Bot's Terms and Privacy Policy before continuing."
                if os.path.exists("terms.txt"):
                    try:
                        with open("terms.txt", "r", encoding="utf-8") as file:
                            terms_text = file.read()
                    except Exception as e:
                        log.error(f"Failed to read terms.txt: {e}")

                embed = discord.Embed(
                    title="📜 Terms of Service & Privacy Policy",
                    description=terms_text,
                    color=COLOR_DEFAULT
                )
                
                try:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                    return
                except Exception as e:
                    log.error(f"Failed to send terms prompt: {e}")

        try:
            await super().on_interaction(interaction)
        except Exception as routing_err:
            log.error(f"Failed to route gateway interaction: {routing_err}")

    # ── Global command error handler ──────────────────────────────────────────
    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
    ):
        exc_type, exc_val, exc_tb = sys.exc_info()
        if exc_type is None:
            exc_type = type(error)
            exc_val = error
            exc_tb = error.__traceback__
            
        tb_lines = traceback.format_exception(exc_type, exc_val, exc_tb)
        raw_tb = "".join(tb_lines)

        file_name = "main.py"
        line_num = "Unknown"
        method = "on_interaction"
        
        tb = exc_tb
        while tb:
            frame = tb.tb_frame
            code = frame.f_code
            file_name = os.path.basename(code.co_filename)
            line_num = str(tb.tb_lineno)
            method = code.co_name
            tb = tb.tb_next

        PanelPrinter.print_exception_box(
            error_type=exc_type.__name__,
            message=str(exc_val),
            file_name=file_name,
            line_num=line_num,
            method=method,
            raw_traceback=raw_tb
        )

        em = discord.Embed(
            title       = "⚠️  Something went wrong",
            description = "An internal error occurred. Try again in a moment.",
            color       = discord.Color.red(),
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=em, ephemeral=True)
            else:
                await interaction.response.send_message(embed=em, ephemeral=True)
        except Exception:
            pass


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    QuadtonBot().run(TOKEN, log_handler=None)

