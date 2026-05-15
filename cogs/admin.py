import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="addcoins", description="[Admin] Add coins to a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def addcoins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await self.db.add_balance(user.id, amount)
        await self.db.add_transaction(user.id, "admin_add", amount, f"Added by admin {interaction.user.name}")
        embed = success_embed(f"Added {format_coin(amount)} to {user.display_name}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removecoins", description="[Admin] Remove coins from a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def removecoins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await self.db.add_balance(user.id, -amount)
        await self.db.add_transaction(user.id, "admin_remove", -amount, f"Removed by admin {interaction.user.name}")
        embed = success_embed(f"Removed {format_coin(amount)} from {user.display_name}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setlevel", description="[Admin] Set a user's level")
    @app_commands.checks.has_permissions(administrator=True)
    async def setlevel(self, interaction: discord.Interaction, user: discord.Member, level: int):
        await self.db.update_user(user.id, level=level, xp=0)
        embed = success_embed(f"Set {user.display_name}'s level to {level}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="giveitem", description="[Admin] Give an item to a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def giveitem(self, interaction: discord.Interaction, user: discord.Member, item_id: int, quantity: int = 1):
        item = await self.db.get_item(item_id)
        if not item:
            return await interaction.response.send_message(embed=error_embed("Item not found!"), ephemeral=True)

        await self.db.add_item(user.id, item_id, quantity)
        embed = success_embed(f"Gave {quantity}x {item['name']} to {user.display_name}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resetuser", description="[Admin] Reset a user's data")
    @app_commands.checks.has_permissions(administrator=True)
    async def resetuser(self, interaction: discord.Interaction, user: discord.Member):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute("DELETE FROM users WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM inventory WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM pets WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM properties WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM user_perks WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM user_potions WHERE user_id = ?", (user.id,))
            await db.execute("DELETE FROM transactions WHERE user_id = ?", (user.id,))
            await db.commit()

        embed = success_embed(f"Reset all data for {user.display_name}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botstats", description="[Admin] View bot statistics")
    @app_commands.checks.has_permissions(administrator=True)
    async def botstats(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            users = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT SUM(balance + bank_balance) FROM users")
            total_coins = (await cursor.fetchone())[0] or 0

            cursor = await db.execute("SELECT COUNT(*) FROM items")
            items = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM market_listings WHERE active = 1")
            listings = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM pets")
            pets = (await cursor.fetchone())[0]

        embed = create_embed("📊 Bot Statistics")
        embed.add_field(name="Users", value=f"{users:,}", inline=True)
        embed.add_field(name="Total Coins", value=f"{total_coins:,}", inline=True)
        embed.add_field(name="Items", value=f"{items}", inline=True)
        embed.add_field(name="Market Listings", value=f"{listings}", inline=True)
        embed.add_field(name="Pets", value=f"{pets}", inline=True)
        embed.add_field(name="Guilds", value=f"{len(self.bot.guilds)}", inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
