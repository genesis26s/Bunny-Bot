import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import json
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, rarity_emoji, check_user_exists

class InventoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="inventory", description="View your inventory")
    async def inventory(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        inv = await self.db.get_inventory(target.id)
        if not inv:
            return await interaction.response.send_message(embed=error_embed("Inventory is empty!"), ephemeral=True)

        embed = create_embed(f"🎒 {target.display_name}'s Inventory")
        for item in inv:
            enchants = json.loads(item['enchantments'])
            en_str = f" ✨{len(enchants)}" if enchants else ""
            eq_str = " [EQUIPPED]" if item['equipped'] else ""
            embed.add_field(
                name=f"{rarity_emoji(item['rarity'])} {item['name']} x{item['quantity']}{en_str}{eq_str}",
                value=f"💰 {item['current_value']:,} | ID: `{item['item_id']}`",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use", description="Use a consumable item")
    async def use(self, interaction: discord.Interaction, item_id: int):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        item = await self.db.get_item(item_id)
        if not item or not item['usable']:
            return await interaction.response.send_message(embed=error_embed("Item not usable!"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?
            """, (interaction.user.id, item_id))
            inv = await cursor.fetchone()
            if not inv:
                return await interaction.response.send_message(embed=error_embed("You don't have this item!"), ephemeral=True)

            if inv[1] == 1:
                await db.execute("DELETE FROM inventory WHERE id = ?", (inv[0],))
            else:
                await db.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (inv[1] - 1, inv[0]))
            await db.commit()

        effects = {
            "Health Potion": (50, "hp"),
            "Bunny Cookie": (20, "xp"),
            "Golden Carrot": (100, "xp"),
        }
        if item['name'] in effects:
            val, typ = effects[item['name']]
            if typ == "xp":
                await self.db.add_xp(interaction.user.id, val)
                msg = f"Gained {val} XP!"
            else:
                msg = "Health restored!"
        else:
            msg = "Item used!"

        embed = success_embed(f"🍾 Used {item['name']}! {msg}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="equip", description="Equip a weapon or armor")
    async def equip(self, interaction: discord.Interaction, item_id: int):
        item = await self.db.get_item(item_id)
        if not item or not item['equipable']:
            return await interaction.response.send_message(embed=error_embed("Item not equipable!"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT inv.id FROM inventory inv
                JOIN items it ON inv.item_id = it.item_id
                WHERE inv.user_id = ? AND it.category = ? AND inv.equipped = 1
            """, (interaction.user.id, item['category']))
            existing = await cursor.fetchone()
            if existing:
                await db.execute("UPDATE inventory SET equipped = 0 WHERE id = ?", (existing[0],))

            cursor = await db.execute("""
                SELECT id FROM inventory WHERE user_id = ? AND item_id = ?
            """, (interaction.user.id, item_id))
            inv = await cursor.fetchone()
            if not inv:
                return await interaction.response.send_message(embed=error_embed("You don't own this!"), ephemeral=True)

            await db.execute("UPDATE inventory SET equipped = 1 WHERE id = ?", (inv[0],))
            await db.commit()

        embed = success_embed(f"⚔️ Equipped {item['name']}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="craft", description="Craft an item from materials")
    async def craft(self, interaction: discord.Interaction, item_id: int):
        item = await self.db.get_item(item_id)
        if not item or not item['craftable']:
            return await interaction.response.send_message(embed=error_embed("Item not craftable!"), ephemeral=True)

        recipes = {
            2: {9: 3},
            3: {10: 3},
            5: {9: 5},
            6: {11: 2},
        }

        recipe = recipes.get(item_id, {})
        if not recipe:
            return await interaction.response.send_message(embed=error_embed("No recipe found!"), ephemeral=True)

        async with aiosqlite.connect(self.db.db_path) as db:
            for req_id, req_qty in recipe.items():
                cursor = await db.execute("""
                    SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?
                """, (interaction.user.id, req_id))
                row = await cursor.fetchone()
                if not row or row[0] < req_qty:
                    req_item = await self.db.get_item(req_id)
                    return await interaction.response.send_message(
                        embed=error_embed(f"Need {req_qty}x {req_item['name']}!"), ephemeral=True
                    )

            for req_id, req_qty in recipe.items():
                await self.db.remove_item(interaction.user.id, req_id, req_qty)

            await self.db.add_item(interaction.user.id, item_id, 1)

        embed = success_embed(f"🔨 Crafted {item['name']}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inspect", description="Inspect an item's details")
    async def inspect(self, interaction: discord.Interaction, item_id: int):
        item = await self.db.get_item(item_id)
        if not item:
            return await interaction.response.send_message(embed=error_embed("Item not found!"), ephemeral=True)

        embed = create_embed(f"{rarity_emoji(item['rarity'])} {item['name']}")
        embed.add_field(name="Description", value=item['description'], inline=False)
        embed.add_field(name="Category", value=item['category'], inline=True)
        embed.add_field(name="Rarity", value=item['rarity'].title(), inline=True)
        embed.add_field(name="Base Value", value=f"{item['base_value']:,}", inline=True)
        embed.add_field(name="Current Value", value=f"{item['current_value']:,}", inline=True)
        embed.add_field(name="Demand", value=f"{item['demand_score']:.1f}", inline=True)
        embed.add_field(name="Supply", value=f"{item['supply_score']:.1f}", inline=True)
        embed.add_field(name="Enchantable", value="Yes" if item['enchantable'] else "No", inline=True)
        embed.add_field(name="Usable", value="Yes" if item['usable'] else "No", inline=True)
        embed.add_field(name="Equipable", value="Yes" if item['equipable'] else "No", inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
