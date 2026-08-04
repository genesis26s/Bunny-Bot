import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT, CURRENCY_SYMBOL

CATALOG = {
    "XP Booster": {"price": 2500, "desc": "Doubles XP gain for 24 hours."},
    "VIP Badge": {"price": 10000, "desc": "Grants prestigious VIP status in profile embeds."},
    "Shield": {"price": 5000, "desc": "Protects your wallet from being robbed."}
}

class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    shop_group = app_commands.Group(name="shop", description="Quadton community store & marketplace")

    @shop_group.command(name="list", description="Browse available items in the Quadton store.")
    async def shop_list(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛒 Quadton Store Catalog", color=COLOR_DEFAULT)
        for name, info in CATALOG.items():
            embed.add_field(name=name, value=f"Price: **{info['price']:,} {CURRENCY_SYMBOL}**\n{info['desc']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @shop_group.command(name="buy", description="Purchase an item from the store.")
    @app_commands.describe(item_name="Name of item to purchase")
    async def shop_buy(self, interaction: discord.Interaction, item_name: str):
        item_cap = item_name.title()
        if item_cap not in CATALOG:
            return await interaction.response.send_message(f"Item `{item_name}` is not sold in the store.", ephemeral=True)

        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)
        cost = CATALOG[item_cap]["price"]

        if user_data["wallet"] < cost:
            return await interaction.response.send_message(f"You need **{cost:,} {CURRENCY_SYMBOL}** to buy this item.", ephemeral=True)

        self.bot.db.update_user(interaction.user.id, wallet=user_data["wallet"] - cost)
        self.bot.db.add_inventory_item(interaction.user.id, item_cap, 1)

        embed = discord.Embed(title="🛍️ Purchase Successful", description=f"You successfully bought **{item_cap}** for **{cost:,} {CURRENCY_SYMBOL}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @shop_group.command(name="sell", description="Sell an item from your inventory back to the shop.")
    @app_commands.describe(item_name="Name of item to sell")
    async def shop_sell(self, interaction: discord.Interaction, item_name: str):
        item_cap = item_name.title()
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        inventory = self.bot.db.get_inventory(interaction.user.id)

        item_row = next((i for i in inventory if i["item_name"].lower() == item_cap.lower()), None)
        if not item_row or item_row["quantity"] <= 0:
            return await interaction.response.send_message("You do not own this item in your inventory.", ephemeral=True)

        base_price = CATALOG.get(item_cap, {"price": 1000})["price"]
        refund = int(base_price * 0.7)

        user_data = self.bot.db.get_user(interaction.user.id)
        self.bot.db.update_user(interaction.user.id, wallet=user_data["wallet"] + refund)
        self.bot.db.remove_inventory_item(interaction.user.id, item_row["item_name"], 1)

        embed = discord.Embed(title="💰 Item Sold", description=f"Sold **{item_cap}** for **{refund:,} {CURRENCY_SYMBOL}**.", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inventory", description="View your personal inventory bag.")
    async def inventory_cmd(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        inv = self.bot.db.get_inventory(interaction.user.id)

        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=COLOR_DEFAULT)
        if not inv:
            embed.description = "Your inventory is currently empty."
        else:
            for row in inv:
                embed.add_field(name=row["item_name"], value=f"Quantity: **{row['quantity']:,}**", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use", description="Use an item from your inventory.")
    @app_commands.describe(item_name="Name of item to consume")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        item_cap = item_name.title()
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        inv = self.bot.db.get_inventory(interaction.user.id)

        item_row = next((i for i in inv if i["item_name"].lower() == item_cap.lower()), None)
        if not item_row or item_row["quantity"] <= 0:
            return await interaction.response.send_message("You do not own this item.", ephemeral=True)

        self.bot.db.remove_inventory_item(interaction.user.id, item_row["item_name"], 1)
        embed = discord.Embed(title="✨ Item Activated", description=f"You successfully consumed and activated **{item_cap}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))

