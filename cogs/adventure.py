import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists, random_chance

class Adventure(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="adventure", description="Go on an adventure")
    @app_commands.checks.cooldown(1, Config.ADVENTURE_COOLDOWN)
    async def adventure(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)

        locations = [
            ("Dark Forest", 100, 300, 50),
            ("Crystal Cave", 200, 500, 80),
            ("Dragon Peak", 500, 1000, 150),
            ("Mystic Ruins", 300, 700, 100),
            ("Bunny Meadow", 50, 150, 30),
        ]
        loc = random.choice(locations)

        if random_chance(0.2):
            embed = error_embed(f"☠️ You died in {loc[0]}! Lost {format_coin(loc[3])} coins.")
            await self.db.add_balance(interaction.user.id, -loc[3])
            await self.db.add_xp(interaction.user.id, 10)
        else:
            coins = random.randint(loc[1], loc[2])
            xp = random.randint(50, 150)

            async with aiosqlite.connect(self.db.db_path) as db:
                cursor = await db.execute("""
                    SELECT effect_value FROM user_perks up
                    JOIN perks_catalog pc ON up.perk_id = pc.perk_id
                    WHERE up.user_id = ? AND pc.effect_type = 'adventure' AND up.active = 1
                """, (interaction.user.id,))
                perk = await cursor.fetchone()
                if perk:
                    coins = int(coins * perk[0])

            item_chance = random_chance(0.3)
            item_msg = ""
            if item_chance:
                async with aiosqlite.connect(self.db.db_path) as db:
                    cursor = await db.execute("""
                        SELECT item_id, name FROM items WHERE category IN ('material', 'collectible', 'consumable')
                        ORDER BY RANDOM() LIMIT 1
                    """)
                    item = await cursor.fetchone()
                    if item:
                        await self.db.add_item(interaction.user.id, item[0], 1)
                        item_msg = f"\n🎁 Found: {item[1]}!"

            await self.db.add_balance(interaction.user.id, coins)
            await self.db.add_xp(interaction.user.id, xp)
            embed = success_embed(
                f"🗺️ Adventure to {loc[0]} successful!\n"
                f"💰 Earned {format_coin(coins)} | +{xp} XP{item_msg}"
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="explore", description="Explore for hidden treasures")
    @app_commands.checks.cooldown(1, 600)
    async def explore(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)

        outcomes = [
            ("found a hidden chest", 0.25, 500, 100),
            ("discovered ancient ruins", 0.15, 1000, 200),
            ("found nothing", 0.4, 0, 10),
            ("fell into a trap", 0.2, -200, 5),
        ]

        roll = random.random()
        cumulative = 0
        for desc, chance, coins, xp in outcomes:
            cumulative += chance
            if roll <= cumulative:
                if coins != 0:
                    await self.db.add_balance(interaction.user.id, coins)
                await self.db.add_xp(interaction.user.id, xp)

                if coins < 0:
                    embed = error_embed(f"😢 You {desc} and lost {format_coin(abs(coins))}!")
                elif coins > 0:
                    embed = success_embed(f"🔍 You {desc} and gained {format_coin(coins)}! +{xp} XP")
                else:
                    embed = create_embed("🍃 Exploration", f"You {desc}. +{xp} XP")
                break
        else:
            embed = create_embed("🍃 Exploration", "Nothing happened. +10 XP")
            await self.db.add_xp(interaction.user.id, 10)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dungeon", description="Enter a dungeon for big rewards")
    @app_commands.checks.cooldown(1, 3600)
    async def dungeon(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['level'] < 10:
            return await interaction.response.send_message(embed=error_embed("Need level 10!"), ephemeral=True)

        rooms = random.randint(3, 8)
        total_coins = 0
        total_xp = 0
        items_found = []

        for i in range(rooms):
            if random_chance(0.15):
                embed = error_embed(f"☠️ You died in room {i+1}! Lost everything from this run.")
                await interaction.response.send_message(embed=embed)
                return

            coins = random.randint(200, 800)
            xp = random.randint(100, 300)
            total_coins += coins
            total_xp += xp

            if random_chance(0.2):
                async with aiosqlite.connect(self.db.db_path) as db:
                    cursor = await db.execute("""
                        SELECT item_id, name, rarity FROM items 
                        WHERE rarity IN ('rare', 'epic', 'legendary') ORDER BY RANDOM() LIMIT 1
                    """)
                    item = await cursor.fetchone()
                    if item:
                        items_found.append(item[1])
                        await self.db.add_item(interaction.user.id, item[0], 1)

        await self.db.add_balance(interaction.user.id, total_coins)
        await self.db.add_xp(interaction.user.id, total_xp)

        item_str = "\n🎁 Found: " + ", ".join(items_found) if items_found else ""
        embed = success_embed(
            f"🏰 Dungeon Cleared! ({rooms} rooms)\n"
            f"💰 {format_coin(total_coins)} | +{total_xp} XP{item_str}"
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
