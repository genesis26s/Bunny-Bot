import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load .env file BEFORE importing config
load_dotenv()

from config import Config
from database import DatabaseManager

# Validate token was loaded
if not Config.BOT_TOKEN or Config.BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    print('❌ ERROR: BUNNY_BOT_TOKEN not found in .env file!')
    print('   Create a .env file with: BUNNY_BOT_TOKEN=your_token_here')
    exit(1)

class BunnyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        super().__init__(
            command_prefix=Config.PREFIX,
            intents=intents,
            help_command=None
        )
        self.db = DatabaseManager(Config.DATABASE)
    
    async def setup_hook(self):
        await self.db.init()
        await self.load_cogs()
        self.tree.on_error = self.on_tree_error
        print(f"✅ Database initialized")
    
    async def load_cogs(self):
        cogs = [
            "cogs.economy", "cogs.banking", "cogs.shop", "cogs.market",
            "cogs.inventory", "cogs.items", "cogs.jobs", "cogs.levels",
            "cogs.adventure", "cogs.gambling", "cogs.pets", "cogs.property",
            "cogs.minigames", "cogs.perks", "cogs.potions", "cogs.admin", "cogs.help"
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
    
    async def on_ready(self):
        print(f"🐰 Bunny-Bot is online!")
        print(f"User: {self.user}")
        print(f"Guilds: {len(self.guilds)}")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"Sync error: {e}")
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"⏰ Cooldown! Wait {error.retry_after:.1f}s.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission!")
        else:
            print(f"Command error: {error}")
    
    async def on_tree_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⏰ Cooldown! Wait {error.retry_after:.1f}s.", ephemeral=True)
            else:
                await interaction.followup.send(f"⏰ Cooldown! Wait {error.retry_after:.1f}s.", ephemeral=True)
        else:
            print(f"App command error: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred!", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred!", ephemeral=True)

bot = BunnyBot()

async def main():
    async with bot:
        await bot.start(Config.BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
