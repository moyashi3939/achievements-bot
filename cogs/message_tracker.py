# cogs/message_tracker.py
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import re

class MessageTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.edit_logs = {}
        self.delete_logs = {}

        # ── 【要件対応】複数キーワード設定場所 ──
        self.alcohol_keywords = ["酒", "ビール", "ストゼロ", "ハイボール", "酎ハイ", "ワイン"] 
        self.cold_laugh_keywords = ["おおw", "うおw", "oow", "uow", "おおｗ", "うおｗ", "うお", "uo","どわーｗ", "どわーw", "どわ-", "どわ-w","dowa-w", "dowa-", "dowaーw","きちーｗ", "きちーw", "kichi-w", "kiti-w", "うぉｗ", "うぉw"]

        self.bad_words_patterns = [
            r"バカ", r"ばか", r"baka",r"馬鹿",
            r"クソ", r"くそ", r"kuso",r"糞",
            r"カス", r"かす", r"kasu",
            r"アホ", r"あほ", r"aho", r"阿呆",
            r"死ね", r"しね", r"shine", r"4ね",
        ]

        # ── ⚠️ 【重要】ここに正しいDiscordのチャンネルID（数字）をそれぞれ設定してください ──
        self.CH_BOSOU = 1544692352038477865      # 16番・29番用：暴走チャンネルのID
        self.CH_ZATSUDAN_1 = 0000000000000000000 # 33番用：ざつだん1のID (実際のIDに書き換えてね)
        self.CH_GUSHI = 1545762453814644867       # 34番用：愚痴・発狂のID
        self.CH_X_SENDEN = 0000000000000000000   # 35番用：X宣伝のID (実際のIDに書き換えてね)
        self.CH_BAUMU_TARGET = 000000000000000000

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content
        user = message.author
        channel = message.channel
        now = datetime.now()

        # スレッド内の場合は親チャンネルのIDも考慮できるようにする
        channel_id = channel.id
        if isinstance(channel, discord.Thread) and channel.parent_id:
            channel_id = channel.parent_id

        ach_cog = self.bot.get_cog("AchievementCog")
        if not ach_cog:
            return

        # 1. 「あなたは管理者じゃないでしょ？」
        if user.display_name == "ぴくせる。" and "ストゼロ" in content:
            await ach_cog.unlock_achievement(user, "not_admin", channel)

        # 2. 「怒りを買うよ？」
        if "ぽこden" in content or "ぽこでん" in content:
            await ach_cog.unlock_achievement(user, "buy_anger", channel)

        # 3. 「私生活管理者」
        if "ピコハン" in content and "ぴくせる" in content:
            await ach_cog.unlock_achievement(user, "private_life_manager", channel)

        # 4. 「マインクラフトプロ？」
        if "シルクタッチ強化" in content:
            await ach_cog.unlock_achievement(user, "minecraft_pro", channel)

       # 6. 「ぽい捨てするなよ？」 (指定チャンネルでの @ばうむ メンション)
        baumu_mentioned = any(m.name == "ばうむ" or m.display_name == "ばうむ" for m in message.mentions)
        
        if baumu_mentioned and channel_id == self.CH_BAUMU_TARGET:
            await ach_cog.unlock_achievement(user, "trash_talk", channel)
            
        # 7. 「うるさい」
        if content.startswith("#") and len(content) >= 15:
            await ach_cog.unlock_achievement(user, "noisy", channel)

        # 10. 「アルハラすんなよ！！！」 (22時以降に酒関連ワード)
        if now.hour >= 22 and any(kw in content for kw in self.alcohol_keywords):
            await ach_cog.unlock_achievement(user, "no_alcohol_ii", channel)

        # 11. 「げんき！！！！」
        if "わんだほい" in content:
            await ach_cog.unlock_achievement(user, "genki", channel)

        # 12. 「...w」 (冷笑系ワード)
        if any(kw in content for kw in self.cold_laugh_keywords):
            await ach_cog.unlock_achievement(user, "cold_laugh", channel)

        # 13. 「もやし」
        if "1" in content:
            await ach_cog.unlock_achievement(user, "moyashi", channel)

        # 14. 「はげちゃうわ」
        if "はげ" in content:
            await ach_cog.unlock_achievement(user, "hage", channel)

        # 16. 「ここは黄昏ではありません」 (暴走ch「以外」で「えらこ掘りたい」)
        if "えらこ掘りたい" in content and channel_id != self.CH_BOSOU:
            await ach_cog.unlock_achievement(user, "not_twilight", channel)

        # 26. 「アモアスですか？」
        if "人狼" in content:
            await ach_cog.unlock_achievement(user, "among_us", channel)

        # 27. 「貴様ッ…音ゲーマーだなっ！！」
        if "ゴママヨ" in content:
            await ach_cog.unlock_achievement(user, "sound_gamer", channel)

        # 28. 「メンション失敗（笑）」
        if "@" in content and not message.mentions and not message.role_mentions and not message.everyone:
            await ach_cog.unlock_achievement(user, "mention_fail", channel)

        # 29. 「淫夢チャンネルはここではないですよ！」 (暴走ch「以外」で「やりますねぇ」)
        if "やりますねぇ" in content and channel_id != self.CH_BOSOU:
            await ach_cog.unlock_achievement(user, "wrong_channel", channel)

        # 30. 「再生できてませんよ」
        if content.startswith("m!p https://"):
            if not user.voice or not user.voice.channel:
                await ach_cog.unlock_achievement(user, "playback_fail", channel)

        # 31. 「無から始まる物語」
        if content == "\u200b":
            await ach_cog.unlock_achievement(user, "nothing_tale", channel)

        # 33. ざつだん1で発言
        if channel_id == self.CH_ZATSUDAN_1:
            await ach_cog.unlock_achievement(user, "zatsudan_1", channel)

        # 34. 愚痴・発狂で発言
        if channel_id == self.CH_GUSHI:
            await ach_cog.unlock_achievement(user, "vomit", channel)

        # 35. X宣伝で発言
        if channel_id == self.CH_X_SENDEN:
            await ach_cog.unlock_achievement(user, "twitter_faction", channel)

        # 36. 「光ってる？」
        if "ぴくせる" in content:
            await ach_cog.unlock_achievement(user, "shining", channel)

        # 37. 「悪口はダメですよ？」
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in self.bad_words_patterns):
            await ach_cog.unlock_achievement(user, "bad_words", channel)

        # 38. 「り……隣人！」
        if "しりとり" in content:
            await ach_cog.unlock_achievement(user, "shiritori", channel)

        # 39. 「そんなダイス使わんやろ」
        if "100d100000" in content:
            await ach_cog.unlock_achievement(user, "dice_madness", channel)

        # 23. 「夜更かしの民」 (深夜2時～朝4時)
        if 2 <= now.hour < 4:
            await ach_cog.unlock_achievement(user, "night_owl", channel)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
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