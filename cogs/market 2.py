import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT, CURRENCY_SYMBOL

COMMODITIES = [
    ("Gold Bar", 5000),
    ("Quantum Tech", 2500),
    ("Quadton Token", 1200),
    ("Energy Crystal", 800)
]

class Market(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._seed_market()

    def _seed_market(self):
        for name, price in COMMODITIES:
            if not self.bot.db.get_market_item(name):
                self.bot.db.add_market_item(name, price)

    market_group = app_commands.Group(name="market", description="Dynamic stock market commodity exchange")

    @market_group.command(name="list", description="View current stock prices and market commodities.")
    async def market_list(self, interaction: discord.Interaction):
        items = self.bot.db.get_market_items()
        embed = discord.Embed(title="📈 Quadton Commodity Exchange", color=COLOR_DEFAULT)
        for item in items:
            embed.add_field(
                name=item["name"],
                value=f"Current Price: **{item['current_price']:,.2f} {CURRENCY_SYMBOL}**\nDemand Index: `{item['demand']:.2f}`",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @market_group.command(name="buy", description="Invest Quad-Coins into a volatile market stock.")
    @app_commands.describe(item_name="Name of commodity", amount="Number of shares to buy")
    async def market_buy(self, interaction: discord.Interaction, item_name: str, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)

        item = self.bot.db.get_market_item(item_name.title())
        if not item:
            return await interaction.response.send_message(f"Commodity `{item_name}` not found.", ephemeral=True)

        cost = int(item["current_price"] * amount)
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)

        if user_data["wallet"] < cost:
            return await interaction.response.send_message(f"You need **{cost:,} {CURRENCY_SYMBOL}** to complete this trade.", ephemeral=True)

        self.bot.db.update_user(interaction.user.id, wallet=user_data["wallet"] - cost)
        self.bot.db.add_inventory_item(interaction.user.id, item["name"], amount)
        self.bot.db.update_market_price(item["name"], 0.05, is_buy=True)

        embed = discord.Embed(title="📊 Stock Purchase Executed", description=f"Successfully purchased **{amount}x {item['name']}** for **{cost:,} {CURRENCY_SYMBOL}**.", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @market_group.command(name="sell", description="Liquidate your stock holdings for Quad-Coins.")
    @app_commands.describe(item_name="Name of commodity", amount="Number of shares to sell")
    async def market_sell(self, interaction: discord.Interaction, item_name: str, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)

        item = self.bot.db.get_market_item(item_name.title())
        if not item:
            return await interaction.response.send_message(f"Commodity `{item_name}` not found.", ephemeral=True)

        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        inv = self.bot.db.get_inventory(interaction.user.id)
        row = next((i for i in inv if i["item_name"].lower() == item["name"].lower()), None)

        if not row or row["quantity"] < amount:
            return await interaction.response.send_message(f"You do not own **{amount}x {item['name']}** in your inventory.", ephemeral=True)

        payout = int(item["current_price"] * amount)
        user_data = self.bot.db.get_user(interaction.user.id)

        self.bot.db.update_user(interaction.user.id, wallet=user_data["wallet"] + payout)
        self.bot.db.remove_inventory_item(interaction.user.id, item["name"], amount)
        self.bot.db.update_market_price(item["name"], 0.05, is_buy=False)

        embed = discord.Embed(title="📉 Stock Liquidation Executed", description=f"Successfully sold **{amount}x {item['name']}** for **{payout:,} {CURRENCY_SYMBOL}**.", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @market_group.command(name="portfolio", description="View your current stock and commodity investments.")
    async def market_portfolio(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        inv = self.bot.db.get_inventory(interaction.user.id)
        market_items = {m["name"]: m["current_price"] for m in self.bot.db.get_market_items()}

        embed = discord.Embed(title=f"💼 {interaction.user.display_name}'s Investment Portfolio", color=COLOR_DEFAULT)
        total_value = 0
        for row in inv:
            if row["item_name"] in market_items:
                val = row["quantity"] * market_items[row["item_name"]]
                total_value += val
                embed.add_field(name=row["item_name"], value=f"Shares: **{row['quantity']:,}**\nEst. Value: **{val:,.2f} {CURRENCY_SYMBOL}**", inline=True)

        embed.set_footer(text=f"Total Portfolio Net Worth: {total_value:,.2f} {CURRENCY_SYMBOL}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Market(bot))

