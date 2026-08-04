import time
import discord
from discord import app_commands
from discord.ext import commands
from config import (
    COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT,
    CURRENCY_NAME, CURRENCY_SYMBOL, CURRENCY_EMOJI,
    STARTING_BALANCE, STARTING_BANK, DAILY_BASE_REWARD, DAILY_STREAK_BONUS
)

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your wallet and bank Quad-Coins balance.")
    @app_commands.describe(user="Optional user to inspect balance")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        self.bot.db.ensure_user(target.id, target.name)
        data = self.bot.db.get_user(target.id)

        wallet = data["wallet"]
        bank = data["bank"]
        total = wallet + bank

        embed = discord.Embed(
            title=f"🪙 {target.display_name}'s Quad-Coins Balance",
            color=COLOR_DEFAULT
        )
        embed.add_field(name="Wallet", value=f"**{wallet:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Bank Account", value=f"**{bank:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Total Net Worth", value=f"**{total:,}** {CURRENCY_SYMBOL} {CURRENCY_EMOJI}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="deposit", description="Deposit Quad-Coins from wallet into your secure bank.")
    @app_commands.describe(amount="Amount of Quad-Coins to deposit (or 'all')")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        data = self.bot.db.get_user(interaction.user.id)
        wallet = data["wallet"]

        if amount.lower() == "all":
            deposit_amt = wallet
        else:
            try:
                deposit_amt = int(amount)
            except ValueError:
                return await interaction.response.send_message("Please provide a valid numeric amount or 'all'.", ephemeral=True)

        if deposit_amt <= 0 or deposit_amt > wallet:
            return await interaction.response.send_message("You do not have enough Quad-Coins in your wallet for this deposit.", ephemeral=True)

        self.bot.db.update_user(interaction.user.id, wallet=wallet - deposit_amt, bank=data["bank"] + deposit_amt)
        embed = discord.Embed(
            title="🏦 Deposit Successful",
            description=f"Successfully deposited **{deposit_amt:,} {CURRENCY_SYMBOL}** into your bank account.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="withdraw", description="Withdraw Quad-Coins from bank to wallet.")
    @app_commands.describe(amount="Amount of Quad-Coins to withdraw (or 'all')")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        data = self.bot.db.get_user(interaction.user.id)
        bank = data["bank"]

        if amount.lower() == "all":
            withdraw_amt = bank
        else:
            try:
                withdraw_amt = int(amount)
            except ValueError:
                return await interaction.response.send_message("Please provide a valid numeric amount or 'all'.", ephemeral=True)

        if withdraw_amt <= 0 or withdraw_amt > bank:
            return await interaction.response.send_message("You do not have enough Quad-Coins in your bank for this withdrawal.", ephemeral=True)

        self.bot.db.update_user(interaction.user.id, wallet=data["wallet"] + withdraw_amt, bank=bank - withdraw_amt)
        embed = discord.Embed(
            title="💸 Withdrawal Successful",
            description=f"Successfully withdrew **{withdraw_amt:,} {CURRENCY_SYMBOL}** to your wallet.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pay", description="Transfer Quad-Coins from your wallet to another member.")
    @app_commands.describe(user="Recipient member", amount="Amount of Quad-Coins to send")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot transfer Quad-Coins to yourself.", ephemeral=True)
        if amount <= 0:
            return await interaction.response.send_message("Transfer amount must be greater than zero.", ephemeral=True)

        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        self.bot.db.ensure_user(user.id, user.name)

        sender_data = self.bot.db.get_user(interaction.user.id)
        if sender_data["wallet"] < amount:
            return await interaction.response.send_message("You do not have enough Quad-Coins in your wallet.", ephemeral=True)

        recipient_data = self.bot.db.get_user(user.id)
        self.bot.db.update_user(interaction.user.id, wallet=sender_data["wallet"] - amount)
        self.bot.db.update_user(user.id, wallet=recipient_data["wallet"] + amount)

        embed = discord.Embed(
            title="🤝 Transfer Complete",
            description=f"Successfully sent **{amount:,} {CURRENCY_SYMBOL}** to {user.mention}.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Complete an hourly shift to earn Quad-Coins.")
    async def work(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        data = self.bot.db.get_user(interaction.user.id)
        
        import random
        earnings = random.randint(150, 450)
        new_wallet = data["wallet"] + earnings
        self.bot.db.update_user(interaction.user.id, wallet=new_wallet)

        embed = discord.Embed(
            title="💼 Shift Completed",
            description=f"You worked hard at your job and earned **+{earnings:,} {CURRENCY_SYMBOL} {CURRENCY_EMOJI}**!",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="beg", description="Beg community members for small Quad-Coins donations.")
    async def beg(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        data = self.bot.db.get_user(interaction.user.id)

        import random
        if random.random() < 0.4:
            return await interaction.response.send_message("Nobody gave you any Quad-Coins today. Tough luck!", ephemeral=True)

        donation = random.randint(10, 100)
        self.bot.db.update_user(interaction.user.id, wallet=data["wallet"] + donation)
        embed = discord.Embed(
            title="🥺 Donation Received",
            description=f"A kind stranger took pity and gave you **+{donation} {CURRENCY_SYMBOL}**!",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily streak reward of Quad-Coins.")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        self.bot.db.ensure_user(user_id, interaction.user.name)
        daily_row = self.bot.db.get_daily(user_id)
        
        now = int(time.time())
        last_claim = daily_row["last_claim"]
        streak = daily_row["streak"]

        if now - last_claim < 86400:
            remaining = 86400 - (now - last_claim)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return await interaction.response.send_message(f"⏱️ You have already claimed your daily reward! Come back in **{hours}h {minutes}m**.", ephemeral=True)

        # Calculate streak bonus
        if now - last_claim < 172800:
            streak += 1
        else:
            streak = 1

        reward = DAILY_BASE_REWARD + (min(streak, 10) * DAILY_STREAK_BONUS)
        user_data = self.bot.db.get_user(user_id)
        
        self.bot.db.update_user(user_id, wallet=user_data["wallet"] + reward)
        self.bot.db.update_daily(user_id, streak)

        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You received **+{reward:,} {CURRENCY_SYMBOL}**! (Current Streak: **{streak} days** 🔥)",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))

