import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class Market(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="market", description="View the player market listings")
    async def market(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT m.id, m.seller_id, m.quantity, m.price_per_unit, m.total_price, m.listed_at,
                       i.name, i.rarity, u.username
                FROM market_listings m
                JOIN items i ON m.item_id = i.item_id
                JOIN users u ON m.seller_id = u.user_id
                WHERE m.active = 1
                ORDER BY m.listed_at DESC LIMIT 25
            """)
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(embed=error_embed("No active listings!"), ephemeral=True)

        embed = create_embed("🏪 Player Market")
        for row in rows:
            lid, seller_id, qty, price, total, listed, name, rarity, seller_name = row
            tax = int(total * Config.MARKET_TAX)
            embed.add_field(
                name=f"📦 {name} x{qty} (ID: {lid})",
                value=f"💰 {price:,}/unit | Total: {total:,}\n👤 {seller_name} | 🏷️ {rarity}\n🧾 Tax: {tax:,}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="list", description="List an item on the market")
    async def list(self, interaction: discord.Interaction, item_id: int, quantity: int, price_per_unit: int):
        if quantity < 1 or price_per_unit < 1:
            return await interaction.response.send_message(embed=error_embed("Invalid values!"), ephemeral=True)
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

            total = price_per_unit * quantity
            now = datetime.now().isoformat()
            await db.execute("""
                INSERT INTO market_listings (seller_id, item_id, quantity, price_per_unit, total_price, listed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (interaction.user.id, item_id, quantity, price_per_unit, total, now))

            if inv[1] == quantity:
                await db.execute("DELETE FROM inventory WHERE id = ?", (inv[0],))
            else:
                await db.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (inv[1] - quantity, inv[0]))

            await db.commit()

        await self.db.update_item_value(item_id, demand_delta=0, supply_delta=quantity)
        embed = success_embed(f"📋 Listed {quantity}x {item['name']} at {format_coin(price_per_unit)}/unit!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlist", description="Remove your market listing")
    async def unlist(self, interaction: discord.Interaction, listing_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT seller_id, item_id, quantity, active FROM market_listings WHERE id = ?
            """, (listing_id,))
            row = await cursor.fetchone()
            if not row:
                return await interaction.response.send_message(embed=error_embed("Listing not found!"), ephemeral=True)
            if row[0] != interaction.user.id:
                return await interaction.response.send_message(embed=error_embed("Not your listing!"), ephemeral=True)
            if row[3] == 0:
                return await interaction.response.send_message(embed=error_embed("Already inactive!"), ephemeral=True)

            await db.execute("UPDATE market_listings SET active = 0 WHERE id = ?", (listing_id,))
            await self.db.add_item(interaction.user.id, row[1], row[2])
            await db.commit()

        embed = success_embed("✅ Listing removed and items returned!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mylistings", description="View your active market listings")
    async def mylistings(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT m.id, m.quantity, m.price_per_unit, m.total_price, i.name
                FROM market_listings m
                JOIN items i ON m.item_id = i.item_id
                WHERE m.seller_id = ? AND m.active = 1
            """, (interaction.user.id,))
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(embed=error_embed("No active listings!"), ephemeral=True)

        embed = create_embed("📋 Your Listings")
        for row in rows:
            lid, qty, price, total, name = row
            embed.add_field(
                name=f"ID: {lid} | {name} x{qty}",
                value=f"💰 {price:,}/unit | Total: {total:,}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="marketbuy", description="Buy from the player market")
    async def marketbuy(self, interaction: discord.Interaction, listing_id: int):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT seller_id, item_id, quantity, price_per_unit, total_price, active
                FROM market_listings WHERE id = ?
            """, (listing_id,))
            row = await cursor.fetchone()
            if not row or row[5] == 0:
                return await interaction.response.send_message(embed=error_embed("Listing not found or inactive!"), ephemeral=True)

            seller_id, item_id, qty, price, total, active = row
            if seller_id == interaction.user.id:
                return await interaction.response.send_message(embed=error_embed("Can't buy your own listing!"), ephemeral=True)

            tax = int(total * Config.MARKET_TAX)
            final_price = total + tax

            cursor = await db.execute("""
                SELECT effect_value FROM user_perks up
                JOIN perks_catalog pc ON up.perk_id = pc.perk_id
                WHERE up.user_id = ? AND pc.effect_type = 'tax' AND up.active = 1
            """, (interaction.user.id,))
            perk = await cursor.fetchone()
            if perk and perk[0] == 0:
                final_price = total

            if user_data['balance'] < final_price:
                return await interaction.response.send_message(embed=error_embed(f"Need {format_coin(final_price)}!"), ephemeral=True)

            await db.execute("UPDATE market_listings SET active = 0 WHERE id = ?", (listing_id,))
            await db.commit()

        await self.db.add_balance(interaction.user.id, -final_price)
        await self.db.add_balance(seller_id, total)
        await self.db.add_item(interaction.user.id, item_id, qty)
        await self.db.update_item_value(item_id, demand_delta=qty, supply_delta=0)
        await self.db.add_transaction(interaction.user.id, "market_buy", -final_price, f"Bought from market #{listing_id}")
        await self.db.add_transaction(seller_id, "market_sell", total, f"Sold on market #{listing_id}")

        embed = success_embed(f"🛒 Bought {qty}x item for {format_coin(final_price)}!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Market(bot))
