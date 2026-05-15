import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import json
import random
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, rarity_emoji, check_user_exists

class Items(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="enchant", description="Enchant an item")
    async def enchant(self, interaction: discord.Interaction, item_id: int):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        item = await self.db.get_item(item_id)
        if not item or not item['enchantable']:
            return await interaction.response.send_message(embed=error_embed("Item not enchantable!"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = 21
            """, (interaction.user.id,))
            scroll = await cursor.fetchone()
            if not scroll:
                return await interaction.response.send_message(embed=error_embed("Need an Enchant Scroll!"), ephemeral=True)

            cursor = await db.execute("""
                SELECT enchantment_id, name, effect_type, effect_value, rarity
                FROM enchantments WHERE applicable_categories LIKE ?
            """, (f'%{item["category"]}%',))
            enchants = await cursor.fetchall()
            if not enchants:
                return await interaction.response.send_message(embed=error_embed("No enchantments for this item!"), ephemeral=True)

            chosen = random.choice(enchants)
            en_id, en_name, en_type, en_val, en_rarity = chosen

            cursor = await db.execute("""
                SELECT id, enchantments FROM inventory WHERE user_id = ? AND item_id = ?
            """, (interaction.user.id, item_id))
            inv = await cursor.fetchone()
            if not inv:
                return await interaction.response.send_message(embed=error_embed("You don't own this item!"), ephemeral=True)

            current = json.loads(inv[1])
            if len(current) >= 3:
                return await interaction.response.send_message(embed=error_embed("Max 3 enchantments!"), ephemeral=True)

            current.append(en_id)

            await db.execute("""
                UPDATE inventory SET enchantments = ? WHERE id = ?
            """, (json.dumps(current), inv[0]))

            if scroll[1] == 1:
                await db.execute("DELETE FROM inventory WHERE id = ?", (scroll[0],))
            else:
                await db.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (scroll[1] - 1, scroll[0]))

            await db.commit()

        embed = success_embed(f"✨ Enchanted {item['name']} with {en_name}!\nEffect: {en_type} +{en_val*100:.0f}%")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Items(bot))
