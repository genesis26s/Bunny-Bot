import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class Pets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="pet", description="View your active pet")
    async def pet(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM pets WHERE user_id = ? AND active = 1
            """, (interaction.user.id,))
            pet = await cursor.fetchone()

        if not pet:
            return await interaction.response.send_message(
                embed=error_embed("No active pet! Use /adopt"), ephemeral=True
            )

        embed = create_embed(f"🐾 {pet[3]} the {pet[2].title()}")
        embed.add_field(name="Level", value=f"{pet[4]}", inline=True)
        embed.add_field(name="XP", value=f"{pet[5]}", inline=True)
        embed.add_field(name="Happiness", value=f"{pet[6]}/100", inline=True)
        embed.add_field(name="Hunger", value=f"{pet[7]}/100", inline=True)
        embed.add_field(name="Strength", value=f"{pet[8]}", inline=True)
        embed.add_field(name="Defense", value=f"{pet[9]}", inline=True)
        embed.add_field(name="Speed", value=f"{pet[10]}", inline=True)
        embed.add_field(name="Intelligence", value=f"{pet[11]}", inline=True)
        embed.add_field(name="Adventures", value=f"{pet[13]}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="adopt", description="Adopt a new pet")
    async def adopt(self, interaction: discord.Interaction, pet_type: str, name: str):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['balance'] < 1000:
            return await interaction.response.send_message(
                embed=error_embed("Need 1,000 coins to adopt!"), ephemeral=True
            )

        valid_types = ["bunny", "dog", "cat", "dragon", "wolf", "fox", "eagle"]
        if pet_type.lower() not in valid_types:
            return await interaction.response.send_message(
                embed=error_embed(f"Valid types: {', '.join(valid_types)}"), ephemeral=True
            )

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM pets WHERE user_id = ?
            """, (interaction.user.id,))
            count = (await cursor.fetchone())[0]
            if count >= 5:
                return await interaction.response.send_message(
                    embed=error_embed("Max 5 pets! Release one first."), ephemeral=True
                )

            await db.execute("""
                UPDATE pets SET active = 0 WHERE user_id = ? AND active = 1
            """, (interaction.user.id,))

            await db.execute("""
                INSERT INTO pets (user_id, pet_type, name, level, xp, happiness, hunger, strength, defense, speed, intelligence, active)
                VALUES (?, ?, ?, 1, 0, 100, 100, 10, 10, 10, 10, 1)
            """, (interaction.user.id, pet_type.lower(), name))
            await db.commit()

        await self.db.add_balance(interaction.user.id, -1000)
        embed = success_embed(f"🐾 You adopted {name} the {pet_type.title()}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="feed", description="Feed your pet")
    @app_commands.checks.cooldown(1, 1800)
    async def feed(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT pet_id, hunger, happiness FROM pets WHERE user_id = ? AND active = 1
            """, (interaction.user.id,))
            pet = await cursor.fetchone()

        if not pet:
            return await interaction.response.send_message(embed=error_embed("No active pet!"), ephemeral=True)

        pet_id, hunger, happiness = pet
        new_hunger = min(100, hunger + 30)
        new_happiness = min(100, happiness + 10)

        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute("""
                UPDATE pets SET hunger = ?, happiness = ? WHERE pet_id = ?
            """, (new_hunger, new_happiness, pet_id))
            await db.commit()

        embed = success_embed(f"🍖 Pet fed! Hunger: {new_hunger}/100 | Happiness: {new_happiness}/100")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="train", description="Train your pet")
    @app_commands.checks.cooldown(1, 3600)
    async def train(self, interaction: discord.Interaction, stat: str):
        valid_stats = ["strength", "defense", "speed", "intelligence"]
        if stat.lower() not in valid_stats:
            return await interaction.response.send_message(
                embed=error_embed(f"Valid stats: {', '.join(valid_stats)}"), ephemeral=True
            )

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute(f"""
                SELECT pet_id, {stat}, xp, level FROM pets WHERE user_id = ? AND active = 1
            """, (interaction.user.id,))
            pet = await cursor.fetchone()

        if not pet:
            return await interaction.response.send_message(embed=error_embed("No active pet!"), ephemeral=True)

        pet_id, current, xp, level = pet
        gain = random.randint(1, 5)
        new_val = current + gain
        new_xp = xp + 20
        new_level = level

        if new_xp >= level * 100:
            new_level = level + 1
            new_xp = 0

        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute(f"""
                UPDATE pets SET {stat} = ?, xp = ?, level = ? WHERE pet_id = ?
            """, (new_val, new_xp, new_level, pet_id))
            await db.commit()

        level_up = " 🎉 Level Up!" if new_level > level else ""
        embed = success_embed(f"💪 {stat.title()} +{gain}! Now {new_val}{level_up}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="petlist", description="View all your pets")
    async def petlist(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT pet_id, pet_type, name, level, active FROM pets WHERE user_id = ?
            """, (interaction.user.id,))
            pets = await cursor.fetchall()

        if not pets:
            return await interaction.response.send_message(embed=error_embed("No pets! Use /adopt"), ephemeral=True)

        embed = create_embed("🐾 Your Pets")
        for pet in pets:
            pid, ptype, name, level, active = pet
            status = "🟢 Active" if active else "⚪ Inactive"
            embed.add_field(name=f"{name} ({ptype.title()})", value=f"Lv{level} | {status}", inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Pets(bot))
