import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_DEFAULT, CURRENCY_SYMBOL, CURRENCY_EMOJI

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    lb_group = app_commands.Group(name="leaderboard", description="Quadton global rankings")

    @lb_group.command(name="wealth", description="View the wealthiest Quad-Coin billionaires.")
    async def lb_wealth(self, interaction: discord.Interaction):
        rows = self.bot.db.get_leaderboard("wealth", 10)
        embed = discord.Embed(title="🪙 Quadton Wealth Leaderboard", color=COLOR_DEFAULT)
        for idx, row in enumerate(rows, 1):
            embed.add_field(name=f"#{idx} — {row['username']}", value=`Net Worth: **{row['total']:,}** {CURRENCY_SYMBOL}`, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @lb_group.command(name="level", description="View highest level commanders.")
    async def lb_level(self, interaction: discord.Interaction):
        rows = self.bot.db.get_leaderboard("level", 10)
        embed = discord.Embed(title="⚔️ Quadton Level Leaderboard", color=COLOR_DEFAULT)
        for idx, row in enumerate(rows, 1):
            embed.add_field(name=f"#{idx} — {row['username']}", value=f"Level: **{row['level']}** (XP: {row['xp']})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rank", description="View your personal level, XP progress card, and stats.")
    async def rank_cmd(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        self.bot.db.ensure_user(target.id, target.name)
        data = self.bot.db.get_user(target.id)

        embed = discord.Embed(title=f"🎖️ {target.display_name}'s Commander Rank", color=COLOR_DEFAULT)
        embed.add_field(name="Level", value=str(data["level"]), inline=True)
        embed.add_field(name="XP Progress", value=f"{data['xp']:,} XP", inline=True)
        embed.add_field(name="Career Title", value=data["job_title"], inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))

