import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, level_xp_required, check_user_exists

class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="rank", description="Check your level and XP")
    async def rank(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        user_data = await check_user_exists(self.db, target.id, target.name)
        xp_needed = level_xp_required(user_data['level'])
        progress = min(100, int((user_data['xp'] / xp_needed) * 100))
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)

        embed = create_embed(f"⭐ {target.display_name}'s Rank")
        embed.add_field(name="Level", value=f"{user_data['level']}", inline=True)
        embed.add_field(name="Prestige", value=f"{user_data['prestige']} ⭐", inline=True)
        embed.add_field(name="XP", value=f"{user_data['xp']:,} / {xp_needed:,}", inline=True)
        embed.add_field(name="Progress", value=f"{bar} {progress}%", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="prestige", description="Prestige and reset for bonuses")
    async def prestige(self, interaction: discord.Interaction):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['level'] < 50:
            return await interaction.response.send_message(embed=error_embed("Need level 50!"), ephemeral=True)
        if user_data['balance'] < Config.PRESTIGE_COST:
            return await interaction.response.send_message(
                embed=error_embed(f"Need {format_coin(Config.PRESTIGE_COST)}!"), ephemeral=True
            )

        await self.db.add_balance(interaction.user.id, -Config.PRESTIGE_COST)
        await self.db.update_user(
            interaction.user.id,
            prestige=user_data['prestige'] + 1,
            level=1,
            xp=0,
            balance=Config.STARTING_BALANCE
        )
        embed = success_embed(
            f"🌟 Prestige {user_data['prestige'] + 1} achieved!\n"
            f"All stats reset with +10% income bonus!"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the global leaderboard")
    async def leaderboard(self, interaction: discord.Interaction, sort_by: str = "balance"):
        valid = ["balance", "bank_balance", "level", "xp", "prestige"]
        if sort_by not in valid:
            sort_by = "balance"

        lb = await self.db.get_leaderboard(sort_by, 10)
        embed = create_embed(f"🏆 Leaderboard - {sort_by.replace('_', ' ').title()}")
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, entry in enumerate(lb):
            medal = medals[i] if i < 10 else f"#{i+1}"
            member = interaction.guild.get_member(entry['user_id'])
            name = member.display_name if member else entry['username']
            embed.add_field(
                name=f"{medal} {name}",
                value=f"Score: {entry['score']:,} | NW: {entry['net_worth']:,} | Lv{entry['level']} P{entry['prestige']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverleaderboard", description="View server leaderboard")
    async def serverleaderboard(self, interaction: discord.Interaction, sort_by: str = "balance"):
        valid = ["balance", "level", "xp"]
        if sort_by not in valid:
            sort_by = "balance"

        members = []
        async with aiosqlite.connect(self.db.db_path) as db:
            for member in interaction.guild.members:
                if member.bot:
                    continue
                cursor = await db.execute(f"""
                    SELECT user_id, username, {sort_by} as score, level, prestige, (balance + bank_balance) as net_worth
                    FROM users WHERE user_id = ?
                """, (member.id,))
                row = await cursor.fetchone()
                if row:
                    members.append(dict(zip([c[0] for c in cursor.description], row)))

        members.sort(key=lambda x: x['score'], reverse=True)
        embed = create_embed(f"🏆 Server Leaderboard - {sort_by.title()}")
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, entry in enumerate(members[:10]):
            medal = medals[i] if i < 10 else f"#{i+1}"
            member = interaction.guild.get_member(entry['user_id'])
            name = member.display_name if member else entry['username']
            embed.add_field(
                name=f"{medal} {name}",
                value=f"Score: {entry['score']:,} | NW: {entry['net_worth']:,} | Lv{entry['level']} P{entry['prestige']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Levels(bot))
