import discord
from config import Config
import random
from discord import app_commands

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


# ====================================================================
#  TERMS & PRIVACY POLICY AGREEMENT VERIFICATION WORKFLOW
# ====================================================================

class TermsAgreementView(discord.ui.View):
    """
    Persistent button view that updates a user's verification profile 
    to accepted status inside the database when clicked.
    """
    def __init__(self, db):
        super().__init__(timeout=None)  # Keeps the button component listening indefinitely
        self.db = db

    @discord.ui.button(label="I Agree to Terms & Policy", style=discord.ButtonStyle.green, custom_id="bunny_bot:agree_terms")
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        username = interaction.user.name
        
        # 1. Ensure their profile row is actively instantiated in the database
        await self.db.get_user(user_id, username)
        
        # 2. Update their compliance column flag to true (1)
        await self.db.execute("UPDATE users SET agreed_to_terms = 1 WHERE user_id = ?", (user_id,))
        
        await interaction.response.send_message(
            "🎉 Thank you! You have accepted the Terms & Policy. You can now use all Bunny Bot commands!", 
            ephemeral=True
        )
        self.stop()


def has_agreed_to_terms(db):
    """
    Global command guard wrapper. Halts bot executions if a user's 
    database flag indicates they have not accepted policies yet.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        user_id = interaction.user.id
        username = interaction.user.name
        
        # Pull or initialize user record using your bot's database engine
        user_data = await db.get_user(user_id, username)
        
        # Intercept and present a prompt if user record lacks validation confirmation
        if not user_data or not getattr(user_data, 'agreed_to_terms', False):
            embed = discord.Embed(
                title="⚖️ Bunny Bot Terms of Service",
                description=(
                    "To ensure a safe environment, you must read and agree to our **Terms & Policy** "
                    "before running commands.\n\n"
                    "🌐 [Read our Terms & Policy Here](https://electedking3-oss.github.io/terms.html)\n"
                    "🔒 [Read our Privacy Policy Here](https://electedking3-oss.github.io/privacy.html)"
                ),
                color=Config.EMBED_COLOR
            )
            embed.set_footer(text="By clicking agree, you acknowledge our policies.")
            
            # Send context notification ephemerally so it stays private to them
            await interaction.response.send_message(
                embed=embed, 
                view=TermsAgreementView(db), 
                ephemeral=True
            )
            return False  # Blocks target block execution context
            
        return True  # Allows command loop execution
    return app_commands.check(predicate)
