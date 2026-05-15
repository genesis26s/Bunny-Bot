import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists

class MiniGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="quiz", description="Answer a trivia question for coins")
    @app_commands.checks.cooldown(1, 300)
    async def quiz(self, interaction: discord.Interaction):
        questions = [
            ("What is the capital of France?", "Paris", ["London", "Berlin", "Madrid"]),
            ("How many continents are there?", "7", ["5", "6", "8"]),
            ("What is 2 + 2 * 2?", "6", ["4", "8", "10"]),
            ("What planet is known as the Red Planet?", "Mars", ["Venus", "Jupiter", "Saturn"]),
            ("Who painted the Mona Lisa?", "Leonardo da Vinci", ["Michelangelo", "Raphael", "Donatello"]),
            ("What is the largest ocean?", "Pacific", ["Atlantic", "Indian", "Arctic"]),
            ("How many sides does a hexagon have?", "6", ["5", "7", "8"]),
            ("What is the chemical symbol for gold?", "Au", ["Ag", "Fe", "Cu"]),
        ]

        q = random.choice(questions)
        question, answer, wrong = q
        options = [answer] + wrong
        random.shuffle(options)

        embed = create_embed("🧠 Trivia Quiz")
        embed.description = question
        for i, opt in enumerate(options):
            embed.add_field(name=f"Option {i+1}", value=opt, inline=True)

        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            guess = msg.content.strip().lower()

            if guess == answer.lower() or guess in [opt.lower() for opt in options if opt.lower() == answer.lower()]:
                prize = random.randint(50, 200)
                await self.db.add_balance(interaction.user.id, prize)
                await self.db.add_xp(interaction.user.id, 25)
                await interaction.followup.send(embed=success_embed(f"🎉 Correct! +{format_coin(prize)} | +25 XP"))
            else:
                await interaction.followup.send(embed=error_embed(f"❌ Wrong! Answer was: {answer}"))
        except:
            await interaction.followup.send(embed=error_embed(f"⏰ Time's up! Answer was: {answer}"))

async def setup(bot):
    await bot.add_cog(MiniGames(bot))
