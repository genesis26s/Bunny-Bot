import logging
import discord
from discord import app_commands
from discord.ext import commands

import database as db
import config
from config import (
    OWNER_IDS, COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT,
    CURRENCY_NAME, CURRENCY_SYMBOL, CURRENCY_EMOJI
)

log = logging.getLogger("quadton-bot.admin")


def is_owner():
    """Custom app_commands check to restrict slash command execution exclusively to bot owners."""
    async def predicate(interaction: discord.Interaction) -> bool:
        # Check if user ID is in config.OWNER_IDS or is application owner
        if interaction.user.id in OWNER_IDS:
            return True
            
        # Fallback check against Discord application owner
        if interaction.client.application and interaction.client.application.owner:
            app_owner = interaction.client.application.owner
            if hasattr(app_owner, "ids"):  # Team ownership
                if interaction.user.id in app_owner.ids:
                    return True
            elif interaction.user.id == app_owner.id:
                return True

        embed = discord.Embed(
            title="⛔ Access Denied",
            description="This command is strictly restricted to **Quadton Bot Owners**.",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return app_commands.check(predicate)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.maintenance_mode = False

    admin_group = app_commands.Group(name="admin", description="Bot Owner Administrative Commands")

    # ── Command 55: Grant Quad-Coins ──────────────────────────────────────────
    @admin_group.command(name="add-coins", description="[Owner Only] Grant Quad-Coins to a specific user.")
    @app_commands.describe(user="Target member", amount="Amount of Quad-Coins to grant")
    @is_owner()
    async def add_coins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)

        db.ensure_user(user.id, user.name)
        user_data = db.get_user(user.id)
        new_wallet = user_data["wallet"] + amount
        db.update_user(user.id, wallet=new_wallet)

        embed = discord.Embed(
            title="🪙 Quad-Coins Granted",
            description=f"Successfully granted **+{amount:,} {CURRENCY_SYMBOL}** ({CURRENCY_NAME}) to {user.mention}.",
            color=COLOR_SUCCESS
        )
        embed.add_field(name="Updated Wallet", value=f"**{new_wallet:,}** {CURRENCY_SYMBOL} {CURRENCY_EMOJI}")
        await interaction.response.send_message(embed=embed)

    # ── Command 56: Remove Quad-Coins ───────────────────────────────────────
    @admin_group.command(name="remove-coins", description="[Owner Only] Deduct Quad-Coins from a user.")
    @app_commands.describe(user="Target member", amount="Amount of Quad-Coins to deduct")
    @is_owner()
    async def remove_coins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)

        db.ensure_user(user.id, user.name)
        user_data = db.get_user(user.id)
        new_wallet = max(0, user_data["wallet"] - amount)
        db.update_user(user.id, wallet=new_wallet)

        embed = discord.Embed(
            title="📉 Quad-Coins Deducted",
            description=f"Successfully deducted **-{amount:,} {CURRENCY_SYMBOL}** from {user.mention}.",
            color=COLOR_ERROR
        )
        embed.add_field(name="Updated Wallet", value=f"**{new_wallet:,}** {CURRENCY_SYMBOL} {CURRENCY_EMOJI}")
        await interaction.response.send_message(embed=embed)

    # ── Command 57: Reset User Data ───────────────────────────────────────────
    @admin_group.command(name="reset-user", description="[Owner Only] Completely wipe a user's economy & profile data.")
    @app_commands.describe(user="Target member to reset")
    @is_owner()
    async def reset_user(self, interaction: discord.Interaction, user: discord.Member):
        db.ensure_user(user.id, user.name)
        
        # Reset user record in SQLite
        db.update_user(
            user.id,
            wallet=config.STARTING_BALANCE,
            bank=config.STARTING_BANK,
            reputation=0,
            level=1,
            xp=0,
            job_title="Unemployed",
            job_rank=0,
            prestige=0
        )

        embed = discord.Embed(
            title="🔄 Account Reset Executed",
            description=f"All Quadton account data for {user.mention} has been restored to default values.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    # ── Command 58: Set Market Stock Prices ──────────────────────────────────
    @admin_group.command(name="set-market", description="[Owner Only] Adjust base price of a market commodity.")
    @app_commands.describe(item_name="Name of item", new_base_price="New base price in QC")
    @is_owner()
    async def set_market(self, interaction: discord.Interaction, item_name: str, new_base_price: int):
        item = db.get_market_item(item_name)
        if not item:
            return await interaction.response.send_message(f"Market item `{item_name}` was not found.", ephemeral=True)

        with db.get_db() as conn:
            conn.execute(
                "UPDATE market SET base_price=?, current_price=? WHERE name=?",
                (new_base_price, float(new_base_price), item_name)
            )

        embed = discord.Embed(
            title="📈 Market Price Override",
            description=f"Adjusted base price for **{item_name}** to **{new_base_price:,} {CURRENCY_SYMBOL}**.",
            color=COLOR_DEFAULT
        )
        await interaction.response.send_message(embed=embed)

    # ── Command 59: Maintenance Mode ─────────────────────────────────────────
    @admin_group.command(name="maintenance", description="[Owner Only] Toggle Quadton Bot economy maintenance mode.")
    @is_owner()
    async def maintenance(self, interaction: discord.Interaction):
        self.maintenance_mode = not self.maintenance_mode
        state_str = "ENABLED 🔴" if self.maintenance_mode else "DISABLED 🟢"
        
        embed = discord.Embed(
            title="⚙️ Maintenance Mode Updated",
            description=f"System Maintenance Mode is now **{state_str}**.",
            color=COLOR_ERROR if self.maintenance_mode else COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    # ── Command 60: Hot Reload Cog ───────────────────────────────────────────
    @admin_group.command(name="reload-cog", description="[Owner Only] Recompile and hot-reload a cog extension.")
    @app_commands.describe(cog_name="Name of cog file (e.g. economy, jobs, admin)")
    @is_owner()
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str):
        target = cog_name.lower().replace("cogs.", "")
        extension_path = f"cogs.{target}"

        try:
            await self.bot.reload_extension(extension_path)
            embed = discord.Embed(
                title="⚡ Cog Hot-Reload Complete",
                description=f"Subsystem extension `{extension_path}` recompiled successfully.",
                color=COLOR_SUCCESS
            )
            await interaction.response.send_message(embed=embed)
            log.info(f"Owner {interaction.user.name} hot-reloaded extension {extension_path}")
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Failed to reload `{extension_path}`:\n```py\n{e}\n```",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))

