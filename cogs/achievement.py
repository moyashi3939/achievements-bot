# cogs/achievement.py
import discord
from discord import app_commands
from discord.ext import commands
from achievements_config import ACHIEVEMENTS

class AchievementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1-3C5WwsC6sC3PnITxf9NFYp4X6V7sMyqEJcyhfpIOIA/edit?usp=drivesdk"

    @app_commands.command(name="実績一覧", description="自分が解除した実績の一覧を表示します")
    async def list_achievements(self, interaction: discord.Interaction):
        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT achievement_id FROM user_achievements WHERE user_id = $1",
                interaction.user.id
            )
        unlocked = [row["achievement_id"] for row in rows]
        
        if not unlocked:
            await interaction.response.send_message("現在解除している実績はありません。", ephemeral=True)
            return

        desc = "\n".join([
            f"✅ **{ACHIEVEMENTS[aid]['name']}** - {ACHIEVEMENTS[aid]['description']}" 
            for aid in unlocked if aid in ACHIEVEMENTS
        ])
        embed = discord.Embed(
            title=f"{interaction.user.name}さんの実績一覧",
            description=desc,
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="スプレッドシート", description="実績管理用のスプレッドシートリンクを表示します")
    async def sheet_link(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 実績管理スプレッドシート",
            description=f"現在の実績一覧や進捗はこちらから確認できます。\n[スプレッドシートを開く]({self.sheet_url})",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def unlock_achievement(self, user: discord.abc.User, achievement_id: str, channel: discord.TextChannel):
        if achievement_id not in ACHIEVEMENTS:
            return

        async with self.bot.db.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                user.id, achievement_id
            )
            if exists:
                return

            await conn.execute(
                "INSERT INTO user_achievements (user_id, achievement_id) VALUES ($1, $2)",
                user.id, achievement_id
            )

        ach = ACHIEVEMENTS[achievement_id]
        embed = discord.Embed(
            title="🏆 実績解除！",
            description=f"{user.mention} が実績 **「{ach['name']}」** を達成しました！\n*{ach['description']}*",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AchievementCog(bot))