import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class Perks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="perks", description="View available perks")
    async def perks(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM perks_catalog")
            perks = await cursor.fetchall()

        embed = create_embed("🎁 Perks Shop")
        for perk in perks:
            pid, name, desc, cost, duration, effect_type, effect_val, max_stack = perk
            duration_str = f"{duration}h" if duration > 0 else "Permanent"
            embed.add_field(
                name=f"{name} ({pid})",
                value=f"{desc}\n💰 {cost:,} | ⏱️ {duration_str} | Effect: {effect_type} {effect_val}x",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buyperk", description="Buy a perk")
    async def buyperk(self, interaction: discord.Interaction, perk_id: str):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM perks_catalog WHERE perk_id = ?", (perk_id,))
            perk = await cursor.fetchone()
            if not perk:
                return await interaction.response.send_message(embed=error_embed("Perk not found!"), ephemeral=True)

            pid, name, desc, cost, duration, effect_type, effect_val, max_stack = perk

            if user_data['balance'] < cost:
                return await interaction.response.send_message(
                    embed=error_embed(f"Need {format_coin(cost)}!"), ephemeral=True
                )

            cursor = await db.execute("""
                SELECT COUNT(*) FROM user_perks WHERE user_id = ? AND perk_id = ? AND active = 1
            """, (interaction.user.id, perk_id))
            active_count = (await cursor.fetchone())[0]
            if active_count >= max_stack:
                return await interaction.response.send_message(
                    embed=error_embed(f"Max {max_stack} active!"), ephemeral=True
                )

            now = datetime.now()
            expires = (now + timedelta(hours=duration)).isoformat() if duration > 0 else None

            await db.execute("""
                INSERT INTO user_perks (user_id, perk_id, activated_at, expires_at, active)
                VALUES (?, ?, ?, ?, 1)
            """, (interaction.user.id, perk_id, now.isoformat(), expires))
            await db.commit()

        await self.db.add_balance(interaction.user.id, -cost)
        embed = success_embed(f"🎁 Bought {name}! Active for {duration}h.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="myperks", description="View your active perks")
    async def myperks(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT up.id, pc.name, pc.effect_type, pc.effect_value, up.expires_at
                FROM user_perks up
                JOIN perks_catalog pc ON up.perk_id = pc.perk_id
                WHERE up.user_id = ? AND up.active = 1
            """, (interaction.user.id,))
            perks = await cursor.fetchall()

        if not perks:
            return await interaction.response.send_message(
                embed=error_embed("No active perks!"), ephemeral=True
            )

        embed = create_embed("🎁 Your Active Perks")
        for perk in perks:
            pid, name, effect_type, effect_val, expires = perk
            if expires:
                exp = datetime.fromisoformat(expires)
                remaining = exp - datetime.now()
                time_str = f"{remaining.seconds // 3600}h left"
            else:
                time_str = "Permanent"
            embed.add_field(
                name=name,
                value=f"Effect: {effect_type} {effect_val}x | {time_str}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Perks(bot))
