# cogs/message_tracker.py
import discord
from discord.ext import commands
from datetime import datetime, timedelta, date
import re
from zoneinfo import ZoneInfo

class MessageTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.edit_logs = {}
        self.delete_logs = {}
        self.stalker_logs = {}  # user_id: [(target_id, timestamp), ...]
        self.energy_logs = {}   # user_id: [timestamp, ...]
        self.alcohol_logs = {}  # user_id: [timestamp, ...]
        self.osoyou_logs = {}   # user_id: date (最後に「おそよう」を解除した日付)
        
        # ── 【深夜の独り言用】チャンネルごとの最後のメッセージ情報 ──
        # channel_id: {"last_time": datetime, "last_author_id": int}
        self.channel_activity = {}

        # ── 【要件対応】複数キーワード設定場所 ──
        self.alcohol_keywords = ["酒", "ビール", "ストゼロ", "ハイボール", "酎ハイ", "ワイン"] 
        self.energy_keywords = ["エンドリ", "エナドリ", "モンスター", "レッドブル", "ZONe"]
        self.cold_laugh_keywords = ["おおw", "うおw", "oow", "uow", "おおｗ", "うおｗ", "うお", "uo","どわーｗ", "どわーw", "どわ-", "どわ-w","dowa-w", "dowa-", "dowaーw","きちーｗ", "きちーw", "kichi-w", "kiti-w", "うぉｗ", "うぉw"]

        self.bad_words_patterns = [
            r"バカ", r"ばか", r"baka",r"馬鹿",
            r"クソ", r"くそ", r"kuso",r"糞",
            r"カス", r"かす", r"kasu",
            r"アホ", r"あほ", r"aho", r"阿呆",
            r"死ね", r"しね", r"shine", r"4ね",
        ]

        # 13時以降の挨拶ワード（大文字小文字を区別せず判定するため小文字で定義）
        self.greeting_keywords = ["おは", "おはよう", "おはよ", "goodmorning", "good morning"]

        # ── ⚠️ 【重要】ここに正しいDiscordのチャンネルID（数字）をそれぞれ設定してください ──
        self.CH_BOSOU = 1544692352038477865      # 16番・29番用：暴走チャンネルのID
        self.CH_ZATSUDAN_1 = 0000000000000000000 # 33番用：ざつだん1のID (実際のIDに書き換えてね)
        self.CH_GUSHI = 1545762453814644867       # 34番用：愚痴・発狂のID
        self.CH_X_SENDEN = 0000000000000000000   # 35番用：X宣伝のID (実際のIDに書き換えてね)
        self.CH_BAUMU_TARGET = 1545779503106887760

    async def check_stalker(self, member: discord.Member, target_author_id: int, channel):
        if not target_author_id or target_author_id == member.id:
            return

        now = datetime.now()
        if member.id not in self.stalker_logs:
            self.stalker_logs[member.id] = []

        # 24時間以内のログだけ残す
        self.stalker_logs[member.id] = [
            (t_id, t) for t_id, t in self.stalker_logs[member.id] 
            if now - t < timedelta(hours=24)
        ]
        self.stalker_logs[member.id].append((target_author_id, now))

        # 同じターゲットに対する回数をカウント
        target_counts = {}
        for t_id, _ in self.stalker_logs[member.id]:
            target_counts[t_id] = target_counts.get(t_id, 0) + 1
            if target_counts[t_id] >= 10:
                ach_cog = self.bot.get_cog("AchievementCog")
                if ach_cog:
                    await ach_cog.unlock_achievement(member, "stalker", channel)
                break

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. まずスラッシュコマンドの応答（他ボット含む）をチェック
        if message.interaction_metadata:
            user = message.interaction_metadata.user
            if not user.bot:
                channel = message.channel
                ach_cog = self.bot.get_cog("AchievementCog")
                
                async with self.bot.db.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO user_command_counts (user_id, count) VALUES ($1, 1)
                        ON CONFLICT (user_id) DO UPDATE SET count = user_command_counts.count + 1
                        """,
                        user.id
                    )
                    cmd_count = await conn.fetchval(
                        "SELECT count FROM user_command_counts WHERE user_id = $1", user.id
                    )
                
                if ach_cog and cmd_count >= 20:
                    await ach_cog.unlock_achievement(user, "bot_best_friend", channel)

        # 2. 通常のメッセージに対する処理（ボットのメッセージはここで弾く）
        if message.author.bot:
            return

        now = datetime.now(ZoneInfo("Asia/Tokyo"))
        today = now.date()
        user = message.author
        channel = message.channel
        content = message.content
        ach_cog = self.bot.get_cog("AchievementCog")
        if not ach_cog:
            return

        # スレッド内の場合は親チャンネルのIDも考慮できるようにする
        channel_id = channel.id
        if isinstance(channel, discord.Thread) and channel.parent_id:
            channel_id = channel.parent_id

        # ストーカー判定用（返信の検知）
        if message.reference and message.reference.message_id:
            try:
                target_msg = message.reference.cached_message
                if not target_msg:
                    target_msg = await channel.fetch_message(message.reference.message_id)
                if target_msg and target_msg.author:
                    await self.check_stalker(user, target_msg.author.id, channel)
            except Exception:
                pass

        # ── 「深夜の独り言」(midnight_monologue) の判定 ──
        if channel_id in self.channel_activity:
            last_info = self.channel_activity[channel_id]
            time_diff = now - last_info["last_time"]
            last_author = last_info["last_author_id"]
            
            if time_diff >= timedelta(hours=1) and last_author != user.id:
                await ach_cog.unlock_achievement(user, "midnight_monologue", channel)
        else:
            await ach_cog.unlock_achievement(user, "midnight_monologue", channel)

        # チャンネルの最終アクティビティを更新
        self.channel_activity[channel_id] = {
            "last_time": now,
            "last_author_id": user.id
        }

        # ── 「おそよう」(osoyou) ──
        if now.hour >= 13 and any(kw in content.lower() for kw in self.greeting_keywords):
            if self.osoyou_logs.get(user.id) != today:
                self.osoyou_logs[user.id] = today
                await ach_cog.unlock_achievement(user, "osoyou", channel)

        # ── 「エナカス」(energy_addict) ──
        if any(kw in content for kw in self.energy_keywords):
            if user.id not in self.energy_logs:
                self.energy_logs[user.id] = []
            
            self.energy_logs[user.id] = [t for t in self.energy_logs[user.id] if now - t < timedelta(minutes=3)]
            self.energy_logs[user.id].append(now)

            if len(self.energy_logs[user.id]) >= 2:
                await ach_cog.unlock_achievement(user, "energy_addict", channel)

        # ── 「酒カス」(no_alcohol_ii) ──
        if now.hour >= 22 and any(kw in content for kw in self.alcohol_keywords):
            if user.id not in self.alcohol_logs:
                self.alcohol_logs[user.id] = []
            
            self.alcohol_logs[user.id] = [t for t in self.alcohol_logs[user.id] if now - t < timedelta(minutes=3)]
            self.alcohol_logs[user.id].append(now)

            if len(self.alcohol_logs[user.id]) >= 2:
                await ach_cog.unlock_achievement(user, "no_alcohol_ii", channel)

        # 各種実績トリガー
        if user.display_name == "ぴくせる。" and "ストゼロ" in content:
            await ach_cog.unlock_achievement(user, "not_admin", channel)

        if "ぽこden" in content or "ぽこでん" in content:
            await ach_cog.unlock_achievement(user, "buy_anger", channel)

        if "ピコハン" in content and "ぴくせる" in content:
            await ach_cog.unlock_achievement(user, "private_life_manager", channel)

        baumu_mentioned = any(m.name == "ばうむ" or m.display_name == "ばうむ" for m in message.mentions)
        if baumu_mentioned and channel_id == self.CH_BAUMU_TARGET:
            await ach_cog.unlock_achievement(user, "trash_talk", channel)

        if content.startswith("#") and len(content) >= 15:
            await ach_cog.unlock_achievement(user, "noisy", channel)

        if "わんだほい" in content:
            await ach_cog.unlock_achievement(user, "genki", channel)

        if any(kw in content for kw in self.cold_laugh_keywords):
            await ach_cog.unlock_achievement(user, "cold_laugh", channel)

        if "1" in content:
            await ach_cog.unlock_achievement(user, "moyashi", channel)

        if "はげ" in content:
            await ach_cog.unlock_achievement(user, "hage", channel)

        if "えらこ掘りたい" in content and channel_id != self.CH_BOSOU:
            await ach_cog.unlock_achievement(user, "not_twilight", channel)

        if "人狼" in content:
            await ach_cog.unlock_achievement(user, "among_us", channel)

        if "ゴママヨ" in content:
            await ach_cog.unlock_achievement(user, "sound_gamer", channel)

        if "@" in content and not message.mentions and not message.role_mentions and not message.mention_everyone:
            await ach_cog.unlock_achievement(user, "mention_fail", channel)

        if "やりますねぇ" in content and channel_id != self.CH_BOSOU:
            await ach_cog.unlock_achievement(user, "wrong_channel", channel)

        if content.startswith("m!p https://"):
            if not user.voice or not user.voice.channel:
                await ach_cog.unlock_achievement(user, "playback_fail", channel)

        if channel_id == self.CH_ZATSUDAN_1:
            await ach_cog.unlock_achievement(user, "zatsudan_1", channel)

        if channel_id == self.CH_GUSHI:
            await ach_cog.unlock_achievement(user, "vomit", channel)

        if channel_id == self.CH_X_SENDEN:
            await ach_cog.unlock_achievement(user, "twitter_faction", channel)

        if "ぴくせる" in content:
            await ach_cog.unlock_achievement(user, "shining", channel)

        if any(re.search(pattern, content, re.IGNORECASE) for pattern in self.bad_words_patterns):
            await ach_cog.unlock_achievement(user, "bad_words", channel)

        if "しりとり" in content:
            await ach_cog.unlock_achievement(user, "shiritori", channel)

        if "100d100000" in content:
            await ach_cog.unlock_achievement(user, "dice_madness", channel)

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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id or payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)
        if not member or not channel:
            return

        ach_cog = self.bot.get_cog("AchievementCog")
        if not ach_cog:
            return

        target_author_id = None
        try:
            target_channel = guild.get_channel(payload.channel_id)
            if target_channel:
                target_message = await target_channel.fetch_message(payload.message_id)
                if target_message and target_message.author:
                    target_author_id = target_message.author.id
        except Exception:
            pass

        async with self.bot.db.acquire() as conn:
            if payload.emoji.is_custom_emoji():
                await conn.execute(
                    """
                    INSERT INTO user_emoji_counts (user_id, count) VALUES ($1, 1)
                    ON CONFLICT (user_id) DO UPDATE SET count = user_emoji_counts.count + 1
                    """,
                    member.id
                )
                emoji_count = await conn.fetchval(
                    "SELECT count FROM user_emoji_counts WHERE user_id = $1", member.id
                )
                if emoji_count >= 100:
                    await ach_cog.unlock_achievement(member, "emoji_artisan", channel)

            if target_author_id and target_author_id != member.id:
                await conn.execute(
                    """
                    INSERT INTO user_reaction_counts (user_id, count) VALUES ($1, 1)
                    ON CONFLICT (user_id) DO UPDATE SET count = user_reaction_counts.count + 1
                    """,
                    member.id
                )
                reaction_count = await conn.fetchval(
                    "SELECT count FROM user_reaction_counts WHERE user_id = $1", member.id
                )
                if reaction_count >= 50:
                    await ach_cog.unlock_achievement(member, "empathy_storm", channel)

        if target_author_id and target_author_id != member.id:
            await self.check_stalker(member, target_author_id, channel)

async def setup(bot):
    await bot.add_cog(MessageTrackerCog(bot))