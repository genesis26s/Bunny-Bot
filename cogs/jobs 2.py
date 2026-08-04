import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT, CURRENCY_SYMBOL, CURRENCY_EMOJI

CAREERS = {
    "Intern": {"rank": 1, "salary": 200, "req_level": 1},
    "Developer": {"rank": 2, "salary": 600, "req_level": 5},
    "Manager": {"rank": 3, "salary": 1500, "req_level": 10},
    "Director": {"rank": 4, "salary": 3500, "req_level": 20},
    "CEO": {"rank": 5, "salary": 8000, "req_level": 35}
}

class Jobs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    job_group = app_commands.Group(name="job", description="Manage your Quadton career and professions")

    @job_group.command(name="list", description="Browse available career positions and salaries.")
    async def job_list(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💼 Quadton Career Directory", color=COLOR_DEFAULT)
        for title, info in CAREERS.items():
            embed.add_field(name=f"{title} (Rank {info['rank']})", value=f"Salary: **{info['salary']:,} {CURRENCY_SYMBOL}** / shift\nReq. Level: {info['req_level']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @job_group.command(name="apply", description="Apply for a new career position.")
    @app_commands.describe(title="Name of the career title")
    async def job_apply(self, interaction: discord.Interaction, title: str):
        title_cap = title.capitalize()
        if title_cap not in CAREERS:
            return await interaction.response.send_message(f"Career `{title}` does not exist. Use `/job list` to view options.", ephemeral=True)

        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)
        job_info = CAREERS[title_cap]

        if user_data["level"] < job_info["req_level"]:
            return await interaction.response.send_message(f"You need to be **Level {job_info['req_level']}** to apply for {title_cap}.", ephemeral=True)

        self.bot.db.update_user(interaction.user.id, job_title=title_cap, job_rank=job_info["rank"])
        embed = discord.Embed(title="🎉 Career Advancement", description=f"You have been hired as a **{title_cap}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @job_group.command(name="shift", description="Work your professional career shift for high salary QC payouts.")
    async def job_shift(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)
        title = user_data["job_title"]

        if title == "Unemployed" or title not in CAREERS:
            return await interaction.response.send_message("You are currently unemployed! Use `/job apply` first.", ephemeral=True)

        salary = CAREERS[title]["salary"]
        new_wallet = user_data["wallet"] + salary
        self.bot.db.update_user(interaction.user.id, wallet=new_wallet)

        embed = discord.Embed(title="💼 Professional Shift Completed", description=f"You completed your shift as a **{title}** and earned **+{salary:,} {CURRENCY_SYMBOL} {CURRENCY_EMOJI}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @job_group.command(name="stats", description="View your current employment status and career standing.")
    async def job_stats(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)
        title = user_data["job_title"]
        salary = CAREERS.get(title, {}).get("salary", 0)

        embed = discord.Embed(title=f"📋 {interaction.user.display_name}'s Career Profile", color=COLOR_DEFAULT)
        embed.add_field(name="Current Position", value=title, inline=True)
        embed.add_field(name="Shift Payout", value=f"{salary:,} {CURRENCY_SYMBOL}", inline=True)
        await interaction.response.send_message(embed=embed)

    @job_group.command(name="resign", description="Resign from your current career position.")
    async def job_resign(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        self.bot.db.update_user(interaction.user.id, job_title="Unemployed", job_rank=0)
        embed = discord.Embed(title="📄 Resignation Accepted", description="You have resigned from your job and are now unemployed.", color=COLOR_DEFAULT)
        await interaction.response.send_message(embed=embed)

    @job_group.command(name="promotion", description="Request a promotion to a higher career tier.")
    async def job_promotion(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)
        current_title = user_data["job_title"]
        
        if current_title == "Unemployed":
            return await interaction.response.send_message("Get a job first using `/job apply`!", ephemeral=True)

        current_rank = CAREERS[current_title]["rank"]
        next_title = next((t for t, info in CAREERS.items() if info["rank"] == current_rank + 1), None)

        if not next_title:
            return await interaction.response.send_message("You are already at the highest executive career rank!", ephemeral=True)

        req_level = CAREERS[next_title]["req_level"]
        if user_data["level"] < req_level:
            return await interaction.response.send_message(f"You need to reach **Level {req_level}** to get promoted to {next_title}.", ephemeral=True)

        self.bot.db.update_user(interaction.user.id, job_title=next_title, job_rank=current_rank + 1)
        embed = discord.Embed(title="🚀 Promoted!", description=f"Congratulations! You have been promoted to **{next_title}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Jobs(bot))

