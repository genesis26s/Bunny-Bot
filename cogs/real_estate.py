import time
import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT, CURRENCY_SYMBOL, CURRENCY_EMOJI

PROPERTIES = {
    "Apartment": {"cost": 25000, "yield": 500},
    "Mansion": {"cost": 150000, "yield": 3500},
    "Skyscraper": {"cost": 1000000, "yield": 25000}
}

class RealEstate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    property_group = app_commands.Group(name="realestate", description="Quadton real estate investment and rental collection")

    @property_group.command(name="list", description="Browse available real estate properties.")
    async def prop_list(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🏰 Quadton Real Estate Market", color=COLOR_DEFAULT)
        for name, info in PROPERTIES.items():
            embed.add_field(name=name, value=f"Purchase Cost: **{info['cost']:,} {CURRENCY_SYMBOL}**\nRental Yield: **{info['yield']:,} {CURRENCY_SYMBOL}** / hour", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @property_group.command(name="buy", description="Purchase a real estate property.")
    @app_commands.describe(property_name="Name of property")
    async def prop_buy(self, interaction: discord.Interaction, property_name: str):
        prop_cap = property_name.title()
        if prop_cap not in PROPERTIES:
            return await interaction.response.send_message(f"Property `{property_name}` does not exist.", ephemeral=True)

        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)
        cost = PROPERTIES[prop_cap]["cost"]

        if user_data["wallet"] < cost:
            return await interaction.response.send_message(f"You need **{cost:,} {CURRENCY_SYMBOL}** in your wallet to purchase this property.", ephemeral=True)

        with self.bot.db.get_db() as conn:
            existing = conn.execute("SELECT * FROM properties WHERE user_id=? AND property_name=?", (interaction.user.id, prop_cap)).fetchone()
            if existing:
                return await interaction.response.send_message("You already own this property!", ephemeral=True)

            conn.execute(
                "INSERT INTO properties (user_id, property_name, level, last_collected) VALUES (?, ?, 1, ?)",
                (interaction.user.id, prop_cap, int(time.time()))
            )

        self.bot.db.update_user(interaction.user.id, wallet=user_data["wallet"] - cost)
        embed = discord.Embed(title="🏡 Property Acquired", description=f"Successfully purchased **{prop_cap}** for **{cost:,} {CURRENCY_SYMBOL}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @property_group.command(name="collect", description="Collect accumulated rental income from your properties.")
    async def prop_collect(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        now = int(time.time())

        with self.bot.db.get_db() as conn:
            props = conn.execute("SELECT * FROM properties WHERE user_id=?", (interaction.user.id,)).fetchall()
            if not props:
                return await interaction.response.send_message("You do not own any real estate properties yet.", ephemeral=True)

            total_yield = 0
            for row in props:
                p_name = row["property_name"]
                hours_passed = (now - row["last_collected"]) / 3600
                if hours_passed >= 1:
                    base_yield = PROPERTIES[p_name]["yield"] * row["level"]
                    earned = int(base_yield * hours_passed)
                    total_yield += earned
                    conn.execute("UPDATE properties SET last_collected=? WHERE user_id=? AND property_name=?", (now, interaction.user.id, p_name))

            if total_yield <= 0:
                return await interaction.response.send_message("Your properties are still generating rent. Come back later!", ephemeral=True)

            user_data = self.bot.db.get_user(interaction.user.id)
            conn.execute("UPDATE users SET wallet=wallet+? WHERE user_id=?", (total_yield, interaction.user.id))

        embed = discord.Embed(title="🪙 Rental Income Collected", description=f"Collected **+{total_yield:,} {CURRENCY_SYMBOL} {CURRENCY_EMOJI}** in rental yield from your properties!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)

    @property_group.command(name="list-owned", description="View all real estate properties you currently own.")
    async def prop_owned(self, interaction: discord.Interaction):
        with self.bot.db.get_db() as conn:
            props = conn.execute("SELECT * FROM properties WHERE user_id=?", (interaction.user.id,)).fetchall()

        embed = discord.Embed(title=f"🏰 {interaction.user.display_name}'s Real Estate Portfolio", color=COLOR_DEFAULT)
        if not props:
            embed.description = "You do not own any properties."
        else:
            for p in props:
                embed.add_field(name=p["property_name"], value=f"Tier Level: **{p['level']}**", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RealEstate(bot))

