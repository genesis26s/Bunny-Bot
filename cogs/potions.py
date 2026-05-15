import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class Potions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="potionshop", description="Browse the potion shop")
    async def potionshop(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM potions_catalog")
            potions = await cursor.fetchall()

        embed = create_embed("🧪 Potion Shop")
        for pot in potions:
            pid, name, desc, effect_type, effect_val, duration, rarity, buy, sell = pot
            embed.add_field(
                name=f"{name} (ID: {pid})",
                value=f"{desc}\nEffect: {effect_type} {effect_val} | Duration: {duration}m\n💰 Buy: {buy:,} | Sell: {sell:,}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buypotion", description="Buy a potion")
    async def buypotion(self, interaction: discord.Interaction, potion_id: int, quantity: int = 1):
        if quantity < 1:
            return await interaction.response.send_message(embed=error_embed("Invalid quantity"), ephemeral=True)

        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM potions_catalog WHERE potion_id = ?", (potion_id,))
            potion = await cursor.fetchone()
            if not potion:
                return await interaction.response.send_message(embed=error_embed("Potion not found!"), ephemeral=True)

            total = potion[7] * quantity
            if user_data['balance'] < total:
                return await interaction.response.send_message(
                    embed=error_embed(f"Need {format_coin(total)}!"), ephemeral=True
                )

            cursor = await db.execute("""
                SELECT id, quantity FROM user_potions WHERE user_id = ? AND potion_id = ?
            """, (interaction.user.id, potion_id))
            existing = await cursor.fetchone()

            if existing:
                await db.execute("""
                    UPDATE user_potions SET quantity = quantity + ? WHERE id = ?
                """, (quantity, existing[0]))
            else:
                from datetime import datetime
                now = datetime.now().isoformat()
                await db.execute("""
                    INSERT INTO user_potions (user_id, potion_id, quantity, brewed_at)
                    VALUES (?, ?, ?, ?)
                """, (interaction.user.id, potion_id, quantity, now))
            await db.commit()

        await self.db.add_balance(interaction.user.id, -total)
        embed = success_embed(f"🧪 Bought {quantity}x {potion[1]} for {format_coin(total)}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="drink", description="Drink a potion")
    async def drink(self, interaction: discord.Interaction, potion_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT up.id, up.quantity, pc.name, pc.effect_type, pc.effect_value, pc.duration_minutes
                FROM user_potions up
                JOIN potions_catalog pc ON up.potion_id = pc.potion_id
                WHERE up.user_id = ? AND up.potion_id = ?
            """, (interaction.user.id, potion_id))
            potion = await cursor.fetchone()

        if not potion:
            return await interaction.response.send_message(embed=error_embed("You don't have this potion!"), ephemeral=True)

        pid, qty, name, effect_type, effect_val, duration = potion

        if qty == 1:
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute("DELETE FROM user_potions WHERE id = ?", (pid,))
                await db.commit()
        else:
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute("UPDATE user_potions SET quantity = ? WHERE id = ?", (qty - 1, pid))
                await db.commit()

        embed = success_embed(f"🧪 Drank {name}!\nEffect: {effect_type} {effect_val} for {duration} minutes.")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Potions(bot))
