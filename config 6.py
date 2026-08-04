import os
import discord

# ── Quadton Bot Identity & Metadata ─────────────────────────────────────────
BOT_NAME = "Quadton Bot"
BOT_VERSION = "5.0.0"
BOT_DESCRIPTION = "An advanced Discord economy, career, market, and RPG system powered by Quad-Coins."
BOT_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("BUNNY_BOT_TOKEN", "")
PREFIX = "!"
DATABASE = "quadton_bot.db"

# ── Bot Owners Security Configuration ───────────────────────────────────────
# List your Discord User IDs here (e.g. [1353160030257549372, 987654321098765432])
# You can also set a comma-separated list in your .env file as OWNER_IDS=123456789,987654321
raw_owner_ids = os.getenv("OWNER_IDS", "")
if raw_owner_ids:
    OWNER_IDS = [int(i.strip()) for i in raw_owner_ids.split(",") if i.strip().isdigit()]
else:
    # Add your personal Discord ID(s) directly into this list:
    OWNER_IDS = [
        123456789012345678,  # Replace with your actual Discord User ID
    ]

# Currency Branding
CURRENCY_NAME = "Quad-Coins"
CURRENCY_SYMBOL = "QC"
CURRENCY_EMOJI = "🪙"

# ── UI & Styling ──────────────────────────────────────────────────────────────
COLOR_DEFAULT = discord.Color.from_rgb(188, 166, 255)  # #bca6ff (Quadton Violet)
COLOR_SUCCESS = discord.Color.from_rgb(46, 196, 182)   # #2ec4b6
COLOR_ERROR   = discord.Color.from_rgb(255, 94, 126)   # #ff5e7e
COLOR_WARNING = discord.Color.from_rgb(243, 163, 51)   # #f3a333

# Hex Integer Constants for legacy views
EMBED_COLOR   = 0xBCA6FF
ERROR_COLOR   = 0xFF5E7E
SUCCESS_COLOR = 0x2EC4B6
GOLD_COLOR    = 0xFFD700

# ── Economy Balance Defaults ──────────────────────────────────────────────────
STARTING_BALANCE = 1000
STARTING_BANK    = 0

# Daily Rewards
DAILY_AMOUNT       = 1000
DAILY_BASE_REWARD  = 500
DAILY_STREAK_BONUS = 100    # Extra QC per day of streak
DAILY_STREAK_MAX   = 10     # Cap streak bonus multiplier at 10 days
WEEKLY_AMOUNT      = 7500

# Work & Crime Commands
WORK_MIN_REWARD       = 100
WORK_MAX_REWARD       = 500
WORK_MIN              = 100
WORK_MAX              = 500
WORK_COOLDOWN_SECONDS = 1800  # 30 Minutes
CRIME_MIN             = 0
CRIME_MAX             = 1000
ROB_CHANCE            = 0.45

# Banking System
BANK_INTEREST_RATE = 0.025
BANK_UPGRADE_COST  = 5000
BANK_LIMIT_BASE    = 25000

# ── Leveling & XP Scaling ─────────────────────────────────────────────────────
XP_PER_LEVEL      = 100
XP_PER_LEVEL_BASE = 100
XP_SCALE_FACTOR   = 1.5     # Formula: Base * (level ** Scale_Factor)
LEVEL_MULTIPLIER  = 1.5
PRESTIGE_COST     = 500000

# ── Gambling ──────────────────────────────────────────────────────────────────
SLOTS_JACKPOT        = 50000
LOTTERY_TICKET       = 250
LOTTERY_JACKPOT_BASE = 25000

# ── Dynamic Market Engine ─────────────────────────────────────────────────────
MARKET_TAX            = 0.05
VALUE_UPDATE_INTERVAL = 3600
DEMAND_SHIFT_BUY      = 0.05  # Demand increase per item bought
SUPPLY_SHIFT_BUY      = 0.02  # Supply decrease per item bought
DEMAND_SHIFT_SELL     = 0.02  # Demand decrease per item sold
SUPPLY_SHIFT_SELL     = 0.05  # Supply increase per item sold

DEMAND_MULTIPLIER     = 0.005
MAX_VALUE_MULTIPLIER  = 5.0
MIN_VALUE_MULTIPLIER  = 0.1

PRICE_CLAMP_LOW       = 0.2   # Min price is 20% of base price
PRICE_CLAMP_HIGH      = 5.0   # Max price is 500% of base price

# ── Adventure & Cooldowns ─────────────────────────────────────────────────────
ADVENTURE_COOLDOWN = 300

# ── System & Logging ──────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"


# ── Backward Compatibility Wrapper Class ──────────────────────────────────────
class Config:
    BOT_TOKEN = BOT_TOKEN
    PREFIX = PREFIX
    DATABASE = DATABASE
    OWNER_IDS = OWNER_IDS
    STARTING_BALANCE = STARTING_BALANCE
    DAILY_AMOUNT = DAILY_AMOUNT
    WEEKLY_AMOUNT = WEEKLY_AMOUNT
    WORK_MIN = WORK_MIN
    WORK_MAX = WORK_MAX
    CRIME_MIN = CRIME_MIN
    CRIME_MAX = CRIME_MAX
    ROB_CHANCE = ROB_CHANCE
    BANK_INTEREST_RATE = BANK_INTEREST_RATE
    BANK_UPGRADE_COST = BANK_UPGRADE_COST
    BANK_LIMIT_BASE = BANK_LIMIT_BASE
    XP_PER_LEVEL = XP_PER_LEVEL
    LEVEL_MULTIPLIER = LEVEL_MULTIPLIER
    PRESTIGE_COST = PRESTIGE_COST
    SLOTS_JACKPOT = SLOTS_JACKPOT
    LOTTERY_TICKET = LOTTERY_TICKET
    LOTTERY_JACKPOT_BASE = LOTTERY_JACKPOT_BASE
    MARKET_TAX = MARKET_TAX
    VALUE_UPDATE_INTERVAL = VALUE_UPDATE_INTERVAL
    ADVENTURE_COOLDOWN = ADVENTURE_COOLDOWN
    EMBED_COLOR = EMBED_COLOR
    ERROR_COLOR = ERROR_COLOR
    SUCCESS_COLOR = SUCCESS_COLOR
    GOLD_COLOR = GOLD_COLOR
    DEMAND_MULTIPLIER = DEMAND_MULTIPLIER
    MAX_VALUE_MULTIPLIER = MAX_VALUE_MULTIPLIER
    MIN_VALUE_MULTIPLIER = MIN_VALUE_MULTIPLIER

