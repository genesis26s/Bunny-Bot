import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from database import DatabaseManager
from config import Config
from utils import create_embed, error_embed, success_embed, format_coin, check_user_exists, random_chance

class Gambling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: DatabaseManager = bot.db

    @app_commands.command(name="slots", description="Play the slot machine")
    async def slots(self, interaction: discord.Interaction, bet: int):
        if bet < 10:
            return await interaction.response.send_message(embed=error_embed("Min bet: 10"), ephemeral=True)
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['balance'] < bet:
            return await interaction.response.send_message(embed=error_embed("Not enough coins!"), ephemeral=True)

        symbols = ["🍒", "🍋", "🍇", "💎", "🐰", "7️⃣"]
        weights = [30, 25, 20, 10, 10, 5]

        result = random.choices(symbols, weights=weights, k=3)

        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute("""
                SELECT effect_value FROM user_perks up
                JOIN perks_catalog pc ON up.perk_id = pc.perk_id
                WHERE up.user_id = ? AND pc.effect_type = 'luck' AND up.active = 1
            """, (interaction.user.id,))
            perk = await cursor.fetchone()

        luck_bonus = perk[0] if perk else 0

        if result[0] == result[1] == result[2]:
            if result[0] == "7️⃣":
                winnings = bet * 50
            elif result[0] == "🐰":
                winnings = bet * 20
            elif result[0] == "💎":
                winnings = bet * 10
            else:
                winnings = bet * 5

            if random_chance(luck_bonus):
                winnings = int(winnings * 1.5)

            await self.db.add_balance(interaction.user.id, winnings - bet)
            embed = success_embed(f"{' '.join(result)}\n🎰 JACKPOT! You won {format_coin(winnings)}!")
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            winnings = bet * 2
            await self.db.add_balance(interaction.user.id, winnings - bet)
            embed = success_embed(f"{' '.join(result)}\n✨ Match! You won {format_coin(winnings)}!")
        else:
            await self.db.add_balance(interaction.user.id, -bet)
            embed = error_embed(f"{' '.join(result)}\n😢 You lost {format_coin(bet)}!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Roll dice against the bot")
    async def dice(self, interaction: discord.Interaction, bet: int):
        if bet < 10:
            return await interaction.response.send_message(embed=error_embed("Min bet: 10"), ephemeral=True)
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['balance'] < bet:
            return await interaction.response.send_message(embed=error_embed("Not enough coins!"), ephemeral=True)

        player = random.randint(1, 6)
        bot_roll = random.randint(1, 6)

        if player > bot_roll:
            await self.db.add_balance(interaction.user.id, bet)
            embed = success_embed(f"🎲 You: {player} | Bot: {bot_roll}\nYou won {format_coin(bet)}!")
        elif player < bot_roll:
            await self.db.add_balance(interaction.user.id, -bet)
            embed = error_embed(f"🎲 You: {player} | Bot: {bot_roll}\nYou lost {format_coin(bet)}!")
        else:
            embed = create_embed("🎲 Tie!", f"Both rolled {player}. Bet returned.")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str):
        if bet < 10:
            return await interaction.response.send_message(embed=error_embed("Min bet: 10"), ephemeral=True)
        choice = choice.lower()
        if choice not in ["heads", "tails"]:
            return await interaction.response.send_message(embed=error_embed("Choose heads or tails!"), ephemeral=True)

        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['balance'] < bet:
            return await interaction.response.send_message(embed=error_embed("Not enough coins!"), ephemeral=True)

        result = random.choice(["heads", "tails"])
        if result == choice:
            await self.db.add_balance(interaction.user.id, bet)
            embed = success_embed(f"🪙 {result.upper()}! You won {format_coin(bet)}!")
        else:
            await self.db.add_balance(interaction.user.id, -bet)
            embed = error_embed(f"🪙 {result.upper()}! You lost {format_coin(bet)}!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lottery", description="Buy a lottery ticket")
    @app_commands.checks.cooldown(1, 86400)
    async def lottery(self, interaction: discord.Interaction, numbers: str):
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['balance'] < Config.LOTTERY_TICKET:
            return await interaction.response.send_message(
                embed=error_embed(f"Need {format_coin(Config.LOTTERY_TICKET)}!"), ephemeral=True
            )

        try:
            picks = [int(x) for x in numbers.split(",")]
            if len(picks) != 3 or any(p < 1 or p > 50 for p in picks):
                raise ValueError
        except:
            return await interaction.response.send_message(
                embed=error_embed("Enter 3 numbers (1-50) separated by commas!"), ephemeral=True
            )

        await self.db.add_balance(interaction.user.id, -Config.LOTTERY_TICKET)
        winning = random.sample(range(1, 51), 3)
        matches = len(set(picks) & set(winning))

        if matches == 3:
            prize = Config.LOTTERY_JACKPOT_BASE * 10
            await self.db.add_balance(interaction.user.id, prize)
            embed = success_embed(f"🎰 JACKPOT! Your numbers: {picks} | Winning: {winning}\nYou won {format_coin(prize)}!")
        elif matches == 2:
            prize = Config.LOTTERY_JACKPOT_BASE
            await self.db.add_balance(interaction.user.id, prize)
            embed = success_embed(f"🎰 2 matches! You won {format_coin(prize)}!")
        elif matches == 1:
            embed = create_embed("🎰 1 match", "You got your ticket price back!")
            await self.db.add_balance(interaction.user.id, Config.LOTTERY_TICKET)
        else:
            embed = error_embed(f"🎰 No matches. Winning: {winning}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="blackjack", description="Play blackjack")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        if bet < 10:
            return await interaction.response.send_message(embed=error_embed("Min bet: 10"), ephemeral=True)
        user_data = await check_user_exists(self.db, interaction.user.id, interaction.user.name)
        if user_data['balance'] < bet:
            return await interaction.response.send_message(embed=error_embed("Not enough coins!"), ephemeral=True)

        def draw_card():
            values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
            suits = ["♠", "♥", "♦", "♣"]
            return (random.choice(values), random.choice(suits))

        def hand_value(hand):
            total = 0
            aces = 0
            for card, _ in hand:
                if card in ["J", "Q", "K"]:
                    total += 10
                elif card == "A":
                    aces += 1
                    total += 11
                else:
                    total += int(card)
            while total > 21 and aces > 0:
                total -= 10
                aces -= 1
            return total

        player_hand = [draw_card(), draw_card()]
        dealer_hand = [draw_card(), draw_card()]

        pv = hand_value(player_hand)
        dv = hand_value(dealer_hand)

        if pv == 21:
            winnings = int(bet * 2.5)
            await self.db.add_balance(interaction.user.id, winnings)
            embed = success_embed(
                f"🃏 BLACKJACK! You: {', '.join([c+s for c,s in player_hand])} ({pv})\n"
                f"Dealer: {', '.join([c+s for c,s in dealer_hand])} ({dv})\n"
                f"You won {format_coin(winnings)}!"
            )
            await interaction.response.send_message(embed=embed)
            return

        # Simple auto-play for slash commands
        while pv < 17:
            player_hand.append(draw_card())
            pv = hand_value(player_hand)

        while dv < 17:
            dealer_hand.append(draw_card())
            dv = hand_value(dealer_hand)

        player_str = ', '.join([c+s for c,s in player_hand])
        dealer_str = ', '.join([c+s for c,s in dealer_hand])

        if pv > 21:
            await self.db.add_balance(interaction.user.id, -bet)
            embed = error_embed(f"🃏 Bust! You: {player_str} ({pv})\nDealer: {dealer_str} ({dv})\nLost {format_coin(bet)}")
        elif dv > 21 or pv > dv:
            await self.db.add_balance(interaction.user.id, bet)
            embed = success_embed(f"🃏 You: {player_str} ({pv})\nDealer: {dealer_str} ({dv})\nWon {format_coin(bet)}!")
        elif pv < dv:
            await self.db.add_balance(interaction.user.id, -bet)
            embed = error_embed(f"🃏 You: {player_str} ({pv})\nDealer: {dealer_str} ({dv})\nLost {format_coin(bet)}")
        else:
            embed = create_embed("🃏 Tie!", f"You: {player_str} ({pv})\nDealer: {dealer_str} ({dv})")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Gambling(bot))
