import discord
from discord import app_commands
from discord.ext import commands
from config import Config
from utils import create_embed

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all Bunny-Bot commands")
    async def help(self, interaction: discord.Interaction, category: str = None):
        embed = create_embed("🐰 Bunny-Bot Help")

        commands_list = {
            "💰 Economy": [
                "/balance - Check your wallet",
                "/daily - Claim daily reward",
                "/weekly - Claim weekly reward",
                "/work - Work for coins",
                "/crime - Commit a crime",
                "/rob - Rob another player",
                "/pay - Send coins to someone",
                "/beg - Beg for coins",
                "/search - Search for coins",
                "/fish - Go fishing",
                "/hunt - Go hunting",
            ],
            "🏦 Banking": [
                "/deposit - Put coins in bank",
                "/withdraw - Take coins from bank",
                "/bank - View bank details",
                "/interest - Collect interest",
                "/upgradebank - Upgrade bank limit",
            ],
            "🛒 Shop & Market": [
                "/shop - Browse items",
                "/buy - Buy an item",
                "/sell - Sell an item",
                "/values - View item values",
                "/market - View player market",
                "/list - List item on market",
                "/unlist - Remove listing",
                "/mylistings - View your listings",
                "/marketbuy - Buy from market",
            ],
            "🎒 Inventory": [
                "/inventory - View inventory",
                "/use - Use consumable",
                "/equip - Equip weapon/armor",
                "/craft - Craft an item",
                "/inspect - Inspect item details",
            ],
            "✨ Items": [
                "/enchant - Enchant an item",
                "/disenchant - Remove enchantments",
            ],
            "💼 Jobs": [
                "/job - View current job",
                "/apply - Apply for a job",
                "/quit - Quit job",
                "/promote - Get promoted",
                "/joblist - View all jobs",
            ],
            "⭐ Levels": [
                "/rank - Check level & XP",
                "/prestige - Prestige reset",
                "/leaderboard - Global leaderboard",
                "/serverleaderboard - Server leaderboard",
            ],
            "🗺️ Adventure": [
                "/adventure - Go on adventure",
                "/explore - Explore for treasure",
                "/dungeon - Enter dungeon",
            ],
            "🎰 Gambling": [
                "/slots - Play slots",
                "/dice - Roll dice",
                "/coinflip - Flip a coin",
                "/lottery - Buy lottery ticket",
                "/blackjack - Play blackjack",
            ],
            "🐾 Pets": [
                "/pet - View active pet",
                "/adopt - Adopt a pet",
                "/feed - Feed your pet",
                "/train - Train your pet",
                "/petlist - View all pets",
                "/petbattle - Battle pets",
            ],
            "🏠 Property": [
                "/property - View properties",
                "/buyproperty - Buy property",
                "/collect - Collect income",
                "/upgradeproperty - Upgrade property",
            ],
            "🎮 Mini-Games": [
                "/quiz - Trivia question",
                "/guess - Guess the number",
                "/rps - Rock Paper Scissors",
                "/trivia - Multiplayer trivia",
            ],
            "🎁 Perks": [
                "/perks - View perks shop",
                "/buyperk - Buy a perk",
                "/myperks - View active perks",
            ],
            "🧪 Potions": [
                "/potionshop - Browse potions",
                "/buypotion - Buy a potion",
                "/mypotions - View your potions",
                "/drink - Drink a potion",
            ],
            "🔧 Admin": [
                "/addcoins - Add coins [Admin]",
                "/removecoins - Remove coins [Admin]",
                "/setlevel - Set level [Admin]",
                "/giveitem - Give item [Admin]",
                "/resetuser - Reset user [Admin]",
                "/botstats - View stats [Admin]",
                "/forcevalue - Set item value [Admin]",
            ],
        }

        if category:
            cat_key = None
            for key in commands_list:
                if category.lower() in key.lower():
                    cat_key = key
                    break
            if cat_key:
                embed.title = f"🐰 {cat_key} Commands"
                embed.description = "\n".join(commands_list[cat_key])
            else:
                embed.description = f"Category '{category}' not found!"
        else:
            for cat, cmds in commands_list.items():
                embed.add_field(name=cat, value=f"{len(cmds)} commands", inline=True)
            embed.description = "Use `/help <category>` for details!\nTotal: 60+ commands"

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guide", description="Beginner's guide to Bunny-Bot")
    async def guide(self, interaction: discord.Interaction):
        embed = create_embed("📖 Beginner's Guide")
        embed.description = """
**Welcome to Bunny-Bot!** 🐰

**Getting Started:**
1. Use `/daily` to claim your first coins
2. Check `/balance` to see your wallet
3. Use `/work` every hour for income
4. Visit `/shop` to buy items

**Economy Basics:**
- 💰 Wallet: Coins you can spend/lose
- 🏦 Bank: Safe storage with interest
- 🪙 Bunny-Coin: The global currency

**Making Money:**
- `/work` - Hourly salary
- `/crime` - Risky but rewarding
- `/fish` & `/hunt` - Gathering
- `/adventure` - Exploration rewards

**Progression:**
- Gain XP to level up
- Prestige at level 50 for bonuses
- Get a job for steady income
- Buy properties for passive income

**Market System:**
- Item values change based on demand/supply
- Buy low, sell high on the player market
- Use `/values` to track trends

**Pets & Properties:**
- `/adopt` a pet for battles
- Buy property deeds from shop
- Collect hourly income from properties
        """
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
