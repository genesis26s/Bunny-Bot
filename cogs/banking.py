import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class Banking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="deposit", description="Deposit coins into your bank")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if amount.lower() == "all":
            dep_amount = user_data['balance']
        else:
            try:
                dep_amount = int(amount)
            except:
                return await interaction.response.send_message(embed=error_embed("Use a number or 'all'"), ephemeral=True)
        if dep_amount <= 0:
            return await interaction.response.send_message(embed=error_embed("Invalid amount"), ephemeral=True)
        if user_data['balance'] < dep_amount:
            return await interaction.response.send_message(embed=error_embed("Not enough coins!"), ephemeral=True)
        space = user_data['bank_limit'] - user_data['bank_balance']
        if space <= 0:
            return await interaction.response.send_message(embed=error_embed("Bank is full! Upgrade it."), ephemeral=True)
        dep_amount = min(dep_amount, space)
        await self.db.add_balance(interaction.user.id, -dep_amount)
        await self.db.add_bank(interaction.user.id, dep_amount)
        await self.db.add_transaction(interaction.user.id, "deposit", dep_amount, "Bank deposit")
        embed = success_embed(f"🏦 Deposited {format_coin(dep_amount)}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="withdraw", description="Withdraw coins from your bank")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if amount.lower() == "all":
            wit_amount = user_data['bank_balance']
        else:
            try:
                wit_amount = int(amount)
            except:
                return await interaction.response.send_message(embed=error_embed("Use a number or 'all'"), ephemeral=True)
        if wit_amount <= 0 or user_data['bank_balance'] < wit_amount:
            return await interaction.response.send_message(embed=error_embed("Not enough in bank!"), ephemeral=True)
        await self.db.add_bank(interaction.user.id, -wit_amount)
        await self.db.add_balance(interaction.user.id, wit_amount)
        await self.db.add_transaction(interaction.user.id, "withdraw", wit_amount, "Bank withdrawal")
        embed = success_embed(f"💸 Withdrew {format_coin(wit_amount)}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bank", description="View your bank details")
    async def bank(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        embed = create_embed("🏦 Bank Account")
        embed.add_field(name="Balance", value=format_coin(user_data['bank_balance']), inline=True)
        embed.add_field(name="Limit", value=format_coin(user_data['bank_limit']), inline=True)
        embed.add_field(name="Space", value=format_coin(user_data['bank_limit'] - user_data['bank_balance']), inline=True)
        interest = int(user_data['bank_balance'] * Config.BANK_INTEREST_RATE)
        embed.add_field(name="Interest Rate", value=f"{Config.BANK_INTEREST_RATE*100}%", inline=True)
        embed.add_field(name="Daily Interest", value=format_coin(interest), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="interest", description="Collect bank interest")
    @app_commands.checks.cooldown(1, 86400)
    async def interest(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        interest = int(user_data['bank_balance'] * Config.BANK_INTEREST_RATE)
        if interest <= 0:
            return await interaction.response.send_message(embed=error_embed("Deposit coins first!"), ephemeral=True)
        await self.db.add_bank(interaction.user.id, interest)
        await self.db.add_transaction(interaction.user.id, "interest", interest, "Bank interest")
        embed = success_embed(f"📈 Collected {format_coin(interest)} in interest!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="upgradebank", description="Upgrade your bank limit")
    async def upgradebank(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        cost = Config.BANK_UPGRADE_COST * (user_data['bank_limit'] // Config.BANK_LIMIT_BASE)
        if user_data['balance'] < cost:
            return await interaction.response.send_message(embed=error_embed(f"Need {format_coin(cost)}!"), ephemeral=True)
        new_limit = user_data['bank_limit'] + Config.BANK_LIMIT_BASE
        await self.db.add_balance(interaction.user.id, -cost)
        await self.db.update_user(interaction.user.id, bank_limit=new_limit)
        await self.db.add_transaction(interaction.user.id, "upgrade", -cost, f"Bank upgrade to {new_limit}")
        embed = success_embed(f"🏦 Bank limit upgraded to {format_coin(new_limit)}!\nCost: {format_coin(cost)}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Banking(bot))
