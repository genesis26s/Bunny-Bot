import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import json
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class Jobs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="job", description="View your current job")
    async def job(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if not user_data['job_id']:
            return await interaction.response.send_message(embed=error_embed("You are unemployed! Use /apply"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (user_data['job_id'],))
            job = await cursor.fetchone()

        if not job:
            return await interaction.response.send_message(embed=error_embed("Job data missing!"), ephemeral=True)

        embed = create_embed(f"💼 {job[1]}")
        embed.add_field(name="Description", value=job[2], inline=False)
        embed.add_field(name="Base Salary", value=format_coin(job[3]), inline=True)
        embed.add_field(name="Promotions", value=f"{user_data['job_promotions']}/{job[4]}", inline=True)
        embed.add_field(name="Bonus", value=format_coin(job[5] * user_data['job_promotions']), inline=True)
        embed.add_field(name="Job EXP", value=f"{user_data['job_exp']}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="apply", description="Apply for a job")
    async def apply(self, interaction: discord.Interaction, job_id: int):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['job_id']:
            return await interaction.response.send_message(embed=error_embed("Quit your current job first! /quit"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            job = await cursor.fetchone()
            if not job:
                return await interaction.response.send_message(embed=error_embed("Job not found!"), ephemeral=True)

            reqs = json.loads(job[6]) if job[6] else {}
            if 'level' in reqs and user_data['level'] < reqs['level']:
                return await interaction.response.send_message(
                    embed=error_embed(f"Need level {reqs['level']}!"), ephemeral=True
                )

            await db.execute("""
                UPDATE users SET job_id = ?, job_exp = 0, job_promotions = 0 WHERE user_id = ?
            """, (job_id, interaction.user.id))
            await db.commit()

        embed = success_embed(f"💼 You are now a {job[1]}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quit", description="Quit your current job")
    async def quit(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if not user_data['job_id']:
            return await interaction.response.send_message(embed=error_embed("You don't have a job!"), ephemeral=True)

        await self.db.update_user(interaction.user.id, job_id=None, job_exp=0, job_promotions=0)
        embed = success_embed("👋 You quit your job!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="promote", description="Get promoted at your job")
    @app_commands.checks.cooldown(1, 86400)
    async def promote(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if not user_data['job_id']:
            return await interaction.response.send_message(embed=error_embed("No job!"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT max_promotions FROM jobs WHERE job_id = ?", (user_data['job_id'],))
            max_promo = (await cursor.fetchone())[0]

        if user_data['job_promotions'] >= max_promo:
            return await interaction.response.send_message(embed=error_embed("Max promotions reached!"), ephemeral=True)

        req_exp = 100 * (user_data['job_promotions'] + 1)
        if user_data['job_exp'] < req_exp:
            return await interaction.response.send_message(
                embed=error_embed(f"Need {req_exp} job EXP! You have {user_data['job_exp']}."), ephemeral=True
            )

        await self.db.update_user(
            interaction.user.id,
            job_promotions=user_data['job_promotions'] + 1,
            job_exp=user_data['job_exp'] - req_exp
        )
        embed = success_embed(f"🎉 Promoted! You are now rank {user_data['job_promotions'] + 1}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="joblist", description="List all available jobs")
    async def joblist(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("SELECT * FROM jobs ORDER BY base_salary ASC")
            jobs = await cursor.fetchall()

        embed = create_embed("💼 Job Board")
        for job in jobs:
            jid, name, desc, salary, max_promo, bonus, reqs = job
            req_str = ""
            if reqs and reqs != "{}":
                r = json.loads(reqs)
                req_str = f" | Req: Lvl {r.get('level', 0)}"
            embed.add_field(
                name=f"ID {jid}: {name}",
                value=f"{desc}\n💰 {salary:,}/work | 📈 {max_promo} promotions{req_str}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Jobs(bot))
