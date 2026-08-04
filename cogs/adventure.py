import random
import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_DEFAULT, CURRENCY_SYMBOL, CURRENCY_EMOJI

class Adventure(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="adventure", description="Embark on a dungeon raid for XP, items, and Quad-Coins.")
    async def adventure(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)

        monsters = ["Goblin Raider", "Skeleton Warrior", "Shadow Assassin", "Cave Troll", "Ancient Dragon"]
        monster = random.choice(monsters)

        success = random.random() > 0.35
        if success:
            loot_qc = random.randint(300, 1200)
            loot_xp = random.randint(50, 150)
            
            new_wallet = user_data["wallet"] + loot_qc
            new_xp = user_data["xp"] + loot_xp
            
            # Level progression check
            current_level = user_data["level"]
            next_lvl_xp = int(100 * (current_level ** 1.5))
            if new_xp >= next_lvl_xp:
                current_level += 1
                new_xp = 0

            self.bot.db.update_user(interaction.user.id, wallet=new_wallet, xp=new_xp, level=current_level)
            
            embed = discord.Embed(
                title="⚔️ Dungeon Raid Victorious!",
                description=f"You successfully defeated a **{monster}**!\n\n**Rewards:**\n+ **{loot_qc:,} {CURRENCY_SYMBOL} {CURRENCY_EMOJI}**\n+ **{loot_xp} XP**",
                color=COLOR_SUCCESS
            )
        else:
            penalty = random.randint(50, 200)
            new_wallet = max(0, user_data["wallet"] - penalty)
            self.bot.db.update_user(interaction.user.id, wallet=new_wallet)

            embed = discord.Embed(
                title="💀 Dungeon Raid Defeat",
                description=f"You were ambushed by a **{monster}** and forced to retreat, dropping **-{penalty} {CURRENCY_SYMBOL}** in the escape.",
                color=COLOR_ERROR
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="explore", description="Search regional wilderness for hidden Quad-Coin treasures.")
    async def explore(self, interaction: discord.Interaction):
        self.bot.db.ensure_user(interaction.user.id, interaction.user.name)
        user_data = self.bot.db.get_user(interaction.user.id)

        if random.random() < 0.4:
            return await interaction.response.send_message("You explored the wilderness for hours but found nothing.", ephemeral=True)

        found = random.randint(50, 350)
        self.bot.db.update_user(interaction.user.id, wallet=user_data["wallet"] + found)

        embed = discord.Embed(title="🧭 Hidden Treasure Discovered", description=f"You searched the ruins and found a hidden chest containing **+{found} {CURRENCY_SYMBOL}**!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Adventure(bot))

