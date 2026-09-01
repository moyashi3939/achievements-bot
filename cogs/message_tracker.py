# cogs/message_tracker.py
import discord
from discord.ext import commands
from datetime import datetime, timedelta

class MessageTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.edit_logs = {}  # user_id: [timestamps]
        self.delete_logs = {} # user_id: [timestamps]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content
        user = message.author
        channel = message.channel
        now = datetime.now()

        ach_cog = self.bot.get_cog("AchievementCog")
        if not ach_cog:
            return

        # 1. 「あなたは管理者じゃないでしょ？」 (名前が「ぴくせる」かつ「ストゼロ」を含む)
        if user.display_name == "ぴくせる" and "ストゼロ" in content:
            await ach_cog.unlock_achievement(user, "not_admin", channel)

        # 2. 「怒りを買うよ？」 ("ぽこでん")
        if "ぽこでん" in content:
            await ach_cog.unlock_achievement(user, "buy_anger", channel)

        # 3. 「私生活管理者」 ("ピコハン" と "ぴくせる")
        if "ピコハン" in content and "ぴくせる" in content:
            await ach_cog.unlock_achievement(user, "private_life_manager", channel)

        # 4. 「マインクラフトプロ？」 ("シルクタッチ強化")
        if "シルクタッチ強化" in content:
            await ach_cog.unlock_achievement(user, "minecraft_pro", channel)

        # 5. 「うるさい」 (#が文頭で15文字以上)
        if content.startswith("#") and len(content) >= 15:
            await ach_cog.unlock_achievement(user, "noisy", channel)

        # 6. 「げんき！！！！」 ("わんだほい")
        if "わんだほい" in content:
            await ach_cog.unlock_achievement(user, "genki", channel)

        # 7. 「もやし」 (文章中に1を含める)
        if "1" in content:
            await ach_cog.unlock_achievement(user, "moyashi", channel)

        # 8. 「はげちゃうわ」 ("はげ")
        if "はげ" in content:
            await ach_cog.unlock_achievement(user, "hage", channel)

        # 9. 「ここは黄昏ではありません」 (暴走ch以外で「えらこ掘りたい」)
        # ※ チャンネル名やIDに合わせて調整してください
        if "えらこ掘りたい" in content and channel.name != "暴走":
            await ach_cog.unlock_achievement(user, "not_twilight", channel)

        # 10. 「夜更かしの民」 (深夜2時〜朝4時)
        if 2 <= now.hour < 4:
            await ach_cog.unlock_achievement(user, "night_owl", channel)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        # 「誤字ですよ」 (1分以内に2回自分のメッセージを編集)
        if not payload.guild_id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild or not payload.cached_message or payload.cached_message.author.bot:
            return

        user = payload.cached_message.author
        channel = guild.get_channel(payload.channel_id)
        now = datetime.now()

        if user.id not in self.edit_logs:
            self.edit_logs[user.id] = []
        
        self.edit_logs[user.id] = [t for t in self.edit_logs[user.id] if now - t < timedelta(minutes=1)]
        self.edit_logs[user.id].append(now)

        if len(self.edit_logs[user.id]) >= 2:
            ach_cog = self.bot.get_cog("AchievementCog")
            if ach_cog and channel:
                await ach_cog.unlock_achievement(user, "typo", channel)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        # 「黒歴史」 (1分以内に3回自分の発言したメッセージを消す - 管理者用実績)
        if not payload.guild_id:
            return
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild or not payload.cached_message or payload.cached_message.author.bot:
            return

        user = payload.cached_message.author
        channel = guild.get_channel(payload.channel_id)
        now = datetime.now()

        if user.id not in self.delete_logs:
            self.delete_logs[user.id] = []

        self.delete_logs[user.id] = [t for t in self.delete_logs[user.id] if now - t < timedelta(minutes=1)]
        self.delete_logs[user.id].append(now)

        if len(self.delete_logs[user.id]) >= 3:
            ach_cog = self.bot.get_cog("AchievementCog")
            if ach_cog and channel:
                await ach_cog.unlock_achievement(user, "black_history", channel)

async def setup(bot):
    await bot.add_cog(MessageTrackerCog(bot))