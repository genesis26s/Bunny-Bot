import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, rarity_emoji, check_user_exists

class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="shop", description="Browse the item shop")
    async def shop(self, interaction: discord.Interaction, category: str = None):
        async with aiosqlite.connect(self.db.db_path) as db:
            if category:
                cursor = await db.execute("""
                    SELECT item_id, name, description, category, current_value, rarity 
                    FROM items WHERE category = ? ORDER BY current_value ASC
                """, (category,))
            else:
                cursor = await db.execute("""
                    SELECT item_id, name, description, category, current_value, rarity 
                    FROM items ORDER BY category, current_value ASC
                """)
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(embed=error_embed("No items found!"), ephemeral=True)

        embed = create_embed("🛒 Bunny Shop")
        current_cat = ""
        for row in rows:
            item_id, name, desc, cat, value, rarity = row
            if cat != current_cat:
                current_cat = cat
                embed.add_field(name=f"📂 {cat.upper()}", value="━" * 20, inline=False)
            emoji = rarity_emoji(rarity)
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"{desc}\n💰 {value:,} | ID: `{item_id}`",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    async def buy(self, interaction: discord.Interaction, item_id: int, quantity: int = 1):
        if quantity < 1:
            return await interaction.response.send_message(embed=error_embed("Invalid quantity"), ephemeral=True)
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        item = await self.db.get_item(item_id)
        if not item:
            return await interaction.response.send_message(embed=error_embed("Item not found!"), ephemeral=True)
        total = item['current_value'] * quantity
        if user_data['balance'] < total:
            return await interaction.response.send_message(embed=error_embed(f"Need {format_coin(total)}!"), ephemeral=True)

        await self.db.add_balance(interaction.user.id, -total)
        await self.db.add_item(interaction.user.id, item_id, quantity)
        await self.db.update_item_value(item_id, demand_delta=quantity, supply_delta=0)
        await self.db.add_transaction(interaction.user.id, "buy", -total, f"Bought {quantity}x {item['name']}")

        embed = success_embed(f"🛒 Bought {quantity}x {item['name']} for {format_coin(total)}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sell", description="Sell an item to the shop")
    async def sell(self, interaction: discord.Interaction, item_id: int, quantity: int = 1):
        if quantity < 1:
            return await interaction.response.send_message(embed=error_embed("Invalid quantity"), ephemeral=True)
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        item = await self.db.get_item(item_id)
        if not item:
            return await interaction.response.send_message(embed=error_embed("Item not found!"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?
            """, (interaction.user.id, item_id))
            inv = await cursor.fetchone()
            if not inv or inv[1] < quantity:
                return await interaction.response.send_message(embed=error_embed("Not enough items!"), ephemeral=True)

        sell_price = int(item['current_value'] * 0.7)
        total = sell_price * quantity
        await self.db.add_balance(interaction.user.id, total)
        await self.db.remove_item(interaction.user.id, item_id, quantity)
        await self.db.update_item_value(item_id, demand_delta=0, supply_delta=quantity)
        await self.db.add_transaction(interaction.user.id, "sell", total, f"Sold {quantity}x {item['name']}")

        embed = success_embed(f"💰 Sold {quantity}x {item['name']} for {format_coin(total)}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="values", description="View current item values and trends")
    async def values(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT name, base_value, current_value, demand_score, supply_score, rarity
                FROM items ORDER BY current_value DESC LIMIT 20
            """)
            rows = await cursor.fetchall()

        embed = create_embed("📈 Item Values & Trends")
        for name, base, current, demand, supply, rarity in rows:
            emoji = rarity_emoji(rarity)
            change = ((current - base) / base) * 100 if base > 0 else 0
            trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Base: {base:,} | Now: {current:,}\n{trend} {change:+.1f}% | D:{demand:.0f} S:{supply:.0f}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Shop(bot))
