import discord
from config import Config
import random

def create_embed(title: str, description: str = "", color: int = Config.EMBED_COLOR) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    return embed

def error_embed(description: str) -> discord.Embed:
    return create_embed("❌ Error", description, Config.ERROR_COLOR)

def success_embed(description: str) -> discord.Embed:
    return create_embed("✅ Success", description, Config.SUCCESS_COLOR)

def format_coin(amount: int) -> str:
    return f"🪙 {amount:,} Bunny-Coins"

def format_number(num: int) -> str:
    return f"{num:,}"

def rarity_emoji(rarity: str) -> str:
    emojis = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "mythic": "🔴"
    }
    return emojis.get(rarity.lower(), "⚪")

def random_chance(percent: float) -> bool:
    return random.random() < percent

def level_xp_required(level: int) -> int:
    return int(Config.XP_PER_LEVEL * (Config.LEVEL_MULTIPLIER ** (level - 1)))

async def check_user_exists(db, user_id: int, username: str = None):
    return await db.get_user(user_id, username)
