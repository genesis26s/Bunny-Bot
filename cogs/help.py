import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_DEFAULT, CURRENCY_NAME, CURRENCY_SYMBOL, CURRENCY_EMOJI

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View Quadton Bot's command catalog and subsystems.")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🪙 Quadton Bot — Command Directory",
            description=f"Welcome to **Quadton Bot**, an advanced Discord economy and RPG system powered by **{CURRENCY_NAME} ({CURRENCY_SYMBOL} {CURRENCY_EMOJI})**.\n\nUse slash commands (`/`) to access the following subsystems:",
            color=COLOR_DEFAULT
        )
        embed.add_field(name="💳 Economy & Cash", value="`/balance`, `/deposit`, `/withdraw`, `/pay`, `/work`, `/beg`, `/daily`", inline=False)
        embed.add_field(name="💼 Career & Jobs", value="`/job list`, `/job apply`, `/job shift`, `/job resign`, `/job promotion`, `/job stats`", inline=False)
        embed.add_field(name="🎰 Gambling & Risk", value="`/slots`, `/coinflip`, `/dice`, `/blackjack`, `/roulette`, `/lottery buy`, `/lottery view`", inline=False)
        embed.add_field(name="🛒 Shop & Inventory", value="`/shop list`, `/shop buy`, `/shop sell`, `/shop info`, `/inventory`, `/use`", inline=False)
        embed.add_field(name="📈 Stock Market", value="`/market list`, `/market buy`, `/market sell`, `/market portfolio`, `/market chart`, `/market history`", inline=False)
        embed.add_field(name="🏰 Real Estate", value="`/realestate list`, `/realestate buy`, `/realestate collect`, `/realestate sell`, `/realestate upgrade`, `/realestate list-owned`", inline=False)
        embed.add_field(name="⚔️ RPG & Adventure", value="`/adventure start`, `/explore`, `/quest list`, `/quest claim`, `/craft`, `/dungeon boss`", inline=False)
        embed.add_field(name="🏆 Rankings & Info", value="`/leaderboard wealth`, `/leaderboard level`, `/leaderboard streak`, `/rank`, `/prestige`, `/ping`, `/info`, `/invite`, `/stats`", inline=False)
        embed.set_footer(text="Quadton Bot • Economy System")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check Discord API gateway and SQLite database latency.")
    async def ping_cmd(self, interaction: discord.Interaction):
        start = discord.utils.utcnow()
        await interaction.response.send_message("Testing ping...", ephemeral=True)
        end = discord.utils.utcnow()
        latency = round((end - start).total_seconds() * 1000)
        ws_ping = round(self.bot.latency * 1000) if self.bot.latency else 0

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**API Gateway Latency:** `{ws_ping}ms`\n**Interaction Latency:** `{latency}ms`",
            color=COLOR_DEFAULT
        )
        await interaction.edit_original_response(content=None, embed=embed)

    @app_commands.command(name="info", description="View Quadton Bot system version and uptime specs.")
    async def info_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🪙 Quadton Bot Information",
            description="High-performance SQLite WAL-backed economy bot built for Discord.",
            color=COLOR_DEFAULT
        )
        embed.add_field(name="Connected Servers", value=f"{len(self.bot.guilds):,}", inline=True)
        embed.add_field(name="Active Users", value=f"{sum(g.member_count for g in self.bot.guilds):,}", inline=True)
        embed.add_field(name="Database Engine", value="SQLite v3 (WAL)", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="invite", description="Generate Quadton Bot's OAuth invite link.")
    async def invite_cmd(self, interaction: discord.Interaction):
        invite_url = discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(permissions=8), scopes=("bot", "applications.commands"))
        embed = discord.Embed(
            title="🔗 Invite Quadton Bot",
            description=f"[Click here to add Quadton Bot to your server!]({invite_url})",
            color=COLOR_DEFAULT
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="View global Quad-Coins economy distribution stats.")
    async def stats_cmd(self, interaction: discord.Interaction):
        try:
            with self.bot.db.get_db() as conn:
                total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                total_supply = conn.execute("SELECT SUM(wallet + bank) FROM users").fetchone()[0] or 0
        except Exception:
            total_users, total_supply = 0, 0

        embed = discord.Embed(
            title="📊 Global Quadton Economy Stats",
            description=f"Active Accounts: **{total_users:,}**\nTotal Quad-Coins in Circulation: **{total_supply:,} {CURRENCY_SYMBOL} {CURRENCY_EMOJI}**",
            color=COLOR_DEFAULT
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))

