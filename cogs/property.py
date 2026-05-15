import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class PropertyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="property", description="View your properties")
    async def property(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM properties WHERE user_id = ?
            """, (interaction.user.id,))
            props = await cursor.fetchall()

        if not props:
            return await interaction.response.send_message(
                embed=error_embed("No properties! Buy deeds from the shop."), ephemeral=True
            )

        embed = create_embed("🏠 Your Properties")
        total_income = 0
        for prop in props:
            pid, uid, ptype, name, level, value, income, last = prop
            total_income += income
            embed.add_field(
                name=f"{name} ({ptype.title()})",
                value=f"Lv{level} | 💰 {income:,}/hr | Worth: {value:,}",
                inline=True
            )
        embed.add_field(name="📊 Total Income", value=f"{total_income:,}/hr", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buyproperty", description="Buy a property using a deed")
    async def buyproperty(self, interaction: discord.Interaction, deed_item_id: int, name: str):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        item = await self.db.get_item(deed_item_id)
        if not item or item['category'] != 'property_deed':
            return await interaction.response.send_message(
                embed=error_embed("Invalid deed!"), ephemeral=True
            )

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?
            """, (interaction.user.id, deed_item_id))
            inv = await cursor.fetchone()
            if not inv:
                return await interaction.response.send_message(
                    embed=error_embed("You don't have this deed!"), ephemeral=True
                )

            property_types = {
                19: ("house", 500, 50),
                20: ("castle", 5000, 500),
            }
            ptype, value, income = property_types.get(deed_item_id, ("land", 100, 10))

            now = datetime.now().isoformat()
            await db.execute("""
                INSERT INTO properties (user_id, property_type, name, value, income_per_hour, last_collection)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (interaction.user.id, ptype, name, value, income, now))

            if inv[1] == 1:
                await db.execute("DELETE FROM inventory WHERE id = ?", (inv[0],))
            else:
                await db.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (inv[1] - 1, inv[0]))

            await db.commit()

        embed = success_embed(f"🏠 Bought {name} ({ptype.title()})!\n💰 Income: {income:,}/hr")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="collect", description="Collect income from all properties")
    @app_commands.checks.cooldown(1, 3600)
    async def collect(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT property_id, income_per_hour, last_collection FROM properties WHERE user_id = ?
            """, (interaction.user.id,))
            props = await cursor.fetchall()

        if not props:
            return await interaction.response.send_message(
                embed=error_embed("No properties to collect from!"), ephemeral=True
            )

        total = 0
        now = datetime.now()
        for prop in props:
            pid, income, last = prop
            last_dt = datetime.fromisoformat(last)
            hours = max(1, int((now - last_dt).total_seconds() // 3600))
            earned = income * hours
            total += earned

            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute("""
                    UPDATE properties SET last_collection = ? WHERE property_id = ?
                """, (now.isoformat(), pid))
                await db.commit()

        await self.db.add_balance(interaction.user.id, total)
        embed = success_embed(f"🏠 Collected {format_coin(total)} from properties!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="upgradeproperty", description="Upgrade a property level")
    async def upgradeproperty(self, interaction: discord.Interaction, property_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT level, value, income_per_hour, name FROM properties 
                WHERE property_id = ? AND user_id = ?
            """, (property_id, interaction.user.id))
            prop = await cursor.fetchone()

        if not prop:
            return await interaction.response.send_message(embed=error_embed("Property not found!"), ephemeral=True)

        level, value, income, name = prop
        cost = value * level
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)

        if user_data['balance'] < cost:
            return await interaction.response.send_message(
                embed=error_embed(f"Need {format_coin(cost)}!"), ephemeral=True
            )

        await self.db.add_balance(interaction.user.id, -cost)
        new_level = level + 1
        new_income = int(income * 1.5)
        new_value = int(value * 1.3)

        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute("""
                UPDATE properties SET level = ?, value = ?, income_per_hour = ? WHERE property_id = ?
            """, (new_level, new_value, new_income, property_id))
            await db.commit()

        embed = success_embed(
            f"🏠 {name} upgraded to Lv{new_level}!\n"
            f"💰 Income: {new_income:,}/hr | Value: {new_value:,}"
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PropertyCog(bot))
