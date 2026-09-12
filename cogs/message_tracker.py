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
        self.spam_logs = {}   # user_id: count (連続メッセージ数)
        self.last_author_id = None # 直前にメッセージを送ったユーザーID
        self.stalker_logs = {}  # user_id: [(target_id, timestamp), ...]
        self.energy_logs = {}   # user_id: [timestamp, ...]
        self.alcohol_logs = {}  # user_id: [timestamp, ...]
        self.sleepy_logs = {}   # user_id: [timestamp, ...]
        self.louder_logs = {}   # user_id: [timestamp, ...]
        self.osoyou_logs = {}   # user_id: date
        
        self.channel_activity = {}

        self.alcohol_keywords = ["酒", "ビール", "ストゼロ", "ハイボール", "酎ハイ", "ワイン"] 
        self.energy_keywords = ["エンドリ", "エナドリ", "モンスター", "レッドブル", "ZONe"]
        self.cold_laugh_keywords = ["おおw", "うおw", "oow", "uow", "おおｗ", "うおｗ", "うお", "uo","どわーｗ", "どわーw", "どわ-", "どわ-w","dowa-w", "dowa-", "dowaーw","きちーｗ", "きちーw", "kichi-w", "kiti-w", "うぉｗ", "うぉw"]

        self.bad_words_patterns = [
            r"バカ", r"ばか", r"baka", r"馬鹿",
            r"クソ", r"くそ", r"kuso", r"糞",
            r"カス", r"かす", r"kasu",
            r"アホ", r"あほ", r"aho", r"阿呆",
            r"死ね", r"しね", r"shine", r"4ね",
        ]

        self.greeting_keywords = ["おは", "おはよう", "おはよ", "goodmorning", "good morning"]

        # ── ⚠️ チャンネルID設定 ──
        self.CH_BOSOU = 1478343447843700848      
        self.CH_ZATSUDAN_1 = 1475833949765767180 
        self.CH_GUSHI = 1476030491722514585      
        self.CH_X_SENDEN = 1479196681760276703   
        self.CH_BAUMU_TARGET = 1478693054104735810
        self.CH_JIKO_SHOUKAI = 1475946982651596882 # 事故紹介chのIDを設定
        self.CH_MESHI_TERO = 1478693054104735810   # 飯テロchのIDを設定

    async def check_stalker(self, member: discord.Member, target_author_id: int, channel):
        if not target_author_id or target_author_id == member.id:
            return

        now = datetime.now()
        if member.id not in self.stalker_logs:
            self.stalker_logs[member.id] = []

        self.stalker_logs[member.id] = [
            (t_id, t) for t_id, t in self.stalker_logs[member.id] 
            if now - t < timedelta(hours=24)
        ]
        self.stalker_logs[member.id].append((target_author_id, now))

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
        # 1. ボットからのメッセージは完全に無視する（入室ログの誤反応を確実に防ぐ）
        if message.author.bot:
            return

        # 2. Discord公式のシステムメッセージ（入室通知など）を無視する
        if message.type != discord.MessageType.default:
            return

        # 3. スラッシュコマンドの応答をチェック
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

        now = datetime.now(ZoneInfo("Asia/Tokyo"))
        today = now.date()
        user = message.author
        channel = message.channel
        content = message.content
        ach_cog = self.bot.get_cog("AchievementCog")
        if not ach_cog:
            return

        channel_id = channel.id
        if isinstance(channel, discord.Thread) and channel.parent_id:
            channel_id = channel.parent_id

        # ストーカー判定用（返信の検知）
        target_is_bot = False
        if message.reference and message.reference.message_id:
            try:
                target_msg = message.reference.cached_message
                if not target_msg:
                    target_msg = await channel.fetch_message(message.reference.message_id)
                if target_msg and target_msg.author:
                    if target_msg.author.bot:
                        target_is_bot = True
                    await self.check_stalker(user, target_msg.author.id, channel)
            except Exception:
                pass

        # ── 連投王 (spam_king) の判定 ──
        if self.last_author_id == user.id:
            self.spam_logs[user.id] = self.spam_logs.get(user.id, 0) + 1
        else:
            self.spam_logs[user.id] = 1
            self.last_author_id = user.id

        if self.spam_logs[user.id] >= 5:
            await ach_cog.unlock_achievement(user, "spam_king", channel)
            self.spam_logs[user.id] = 0

        # ── 追加実績の判定群 ──
        # 40: 秘密主義 (スポイラー)
        if "||" in content and content.count("||") >= 2:
            await ach_cog.unlock_achievement(user, "secretive", channel)

        # 41: Shadow Shadow
        if "孤独" in content:
            await ach_cog.unlock_achievement(user, "shadow_shadow", channel)

        # 42: メズマイライザー
        if "誰か助けてね" in content:
            await ach_cog.unlock_achievement(user, "mezumizer", channel)

        # 43: 絶対ジャスティス！
        if "引きこもり" in content:
            await ach_cog.unlock_achievement(user, "absolute_justice", channel)

        # 44: あたしってなんごっけ
        if "わからない" in content:
            await ach_cog.unlock_achievement(user, "what_was_i", channel)

        # 45: 取り繕っていたいな
        if "化石" in content:
            await ach_cog.unlock_achievement(user, "fossil", channel)

        # 46: 僕は何も知らない
        if "知らない" in content:
            await ach_cog.unlock_achievement(user, "i_know_nothing", channel)

        # 47: 神への反逆 (実績botへの返信)
        if "@Acievements Bot" in content:
            await ach_cog.unlock_achievement(user, "rebellion_god", channel)

        # 48: たーまやー
        if "爆死" in content:
            await ach_cog.unlock_achievement(user, "tamaya", channel)

        # 49: あんたばかぁ？ (自分自身をメンション)
        if user in message.mentions:
            await ach_cog.unlock_achievement(user, "anta_baka", channel)

        # 50: まずは事故紹介から
        if channel_id == self.CH_JIKO_SHOUKAI:
            await ach_cog.unlock_achievement(user, "self_intro_first", channel)

        # 51: Good night (21時〜2時におやすみ)
        if (now.hour >= 21 or now.hour < 2) and "おやすみ" in content:
            await ach_cog.unlock_achievement(user, "good_night", channel)

        # 52: 整地してくるわ
        if "マイクラ" in content.lower() or "マインクラフト" in content.lower():
            await ach_cog.unlock_achievement(user, "seichi", channel)

        # 53: 眠くないの？ (深夜4時〜6時に「おはよう」)
        if 4 <= now.hour < 6 and "おはよう" in content:
            await ach_cog.unlock_achievement(user, "not_sleepy", channel)

        # 54: なんでや！阪神関係ないやろ！
        if "33-4" in content or "334" in content:
            await ach_cog.unlock_achievement(user, "hanshin", channel)

        # 55: 鯖主の命
        if "ストゼロ" in content or "ストロングゼロ" in content:
            await ach_cog.unlock_achievement(user, "saba_no_inochi", channel)

        # 56: R'E'A'C'H'
        if "お手を拝借" in content:
            await ach_cog.unlock_achievement(user, "reach", channel)

        # 57: 消えぬ過ち
        if "じろりんぐ" in content.lower() or "ziroring" in content.lower():
            await ach_cog.unlock_achievement(user, "past_mistake", channel)

        # 58: らりあっとじゃねぇよ
        if "わっしょいらりあっと" in content:
            await ach_cog.unlock_achievement(user, "rariat_no_ne_yo", channel)

        # 60: 飯を食え、飯を
        if channel_id == self.CH_MESHI_TERO and message.attachments:
            await ach_cog.unlock_achievement(user, "eat_rice", channel)

        # 61: 悲劇的ビフォーアフター
        if "解体" in content:
            await ach_cog.unlock_achievement(user, "before_after", channel)

        # 64: 逃げるな
        if "ノーツが抜けた" in content:
            await ach_cog.unlock_achievement(user, "dont_run", channel)

        if "哺乳瓶をかかえた酒カスのホイ中退が行く酔っぱらい日記" in content:
            await ach_cog.unlock_achievement(user, "what_diary", channel)

        # 66, 67, 68: maimai系
        if "maimai" in content.lower():
            await ach_cog.unlock_achievement(user, "public_washer", channel)
        if "洗濯機" in content:
            await ach_cog.unlock_achievement(user, "maimai_q", channel)
        if any(k in content for k in ["オンゲキ", "CHUNITHM", "maimai"]):
            await ach_cog.unlock_achievement(user, "gekichumai", channel)

        # 69: お嬢じゃないなり
        if "お嬢" in content or "ゆーと嬢" in content:
            await ach_cog.unlock_achievement(user, "ojou_janai", channel)

        # 70: folern
        if "ｺﾝｽｨｰﾔ" in content:
            await ach_cog.unlock_achievement(user, "folern", channel)

        # 71: Happybirthday!!!!
        if "誕生日" in content:
            await ach_cog.unlock_achievement(user, "happy_birthday", channel)

        # 72: だだから怒りを買うよって
        if "玄米" in content:
            await ach_cog.unlock_achievement(user, "buy_anger_2", channel)

        # 73: いやあああぁぁぁぁぁぁぁ
        if "ゴキブリ" in content:
            await ach_cog.unlock_achievement(user, "cockroach", channel)

        # 75: さっさと寝る (24時間以内に「ねむい」を5回)
        if "ねむい" in content:
            if user.id not in self.sleepy_logs:
                self.sleepy_logs[user.id] = []
            self.sleepy_logs[user.id] = [t for t in self.sleepy_logs[user.id] if now - t < timedelta(hours=24)]
            self.sleepy_logs[user.id].append(now)
            if len(self.sleepy_logs[user.id]) >= 5:
                await ach_cog.unlock_achievement(user, "sleep_early", channel)

        # 76: もっと大きな声で！ (-# で始まる文章を3回連続)
        if content.startswith("-#"):
            if user.id not in self.louder_logs:
                self.louder_logs[user.id] = []
            self.louder_logs[user.id] = [t for t in self.louder_logs[user.id] if now - t < timedelta(minutes=10)]
            self.louder_logs[user.id].append(now)
            if len(self.louder_logs[user.id]) >= 3:
                await ach_cog.unlock_achievement(user, "louder", channel)

        # 77: 英語ペラペラ？ (英数字と半角記号のみで50文字以上)
        if len(content) >= 50 and bool(re.match(r'^[a-zA-Z0-9\s!-\/:-@[-`{-~]+$', content)):
            await ach_cog.unlock_achievement(user, "english_pro", channel)

        # 78: 怪談は夏にお願いします (名前に「八尺」が含まれ、かつ「ポ」または「ﾎ」のみのメッセージ)
        if "八尺" in user.display_name and content in ["ポ", "ﾎ"]:
            await ach_cog.unlock_achievement(user, "ghost_story", channel)

        # 80: ゴミも同然♪
        if "無能" in content:
            await ach_cog.unlock_achievement(user, "trash_same", channel)

        # ── 既存の各種実績トリガー ──
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

        if "えらこほりたい" in content and channel_id != self.CH_BOSOU:
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

        # 深夜の独り言
        if 0 <= now.hour < 4:
            if channel_id in self.channel_activity:
                last_info = self.channel_activity[channel_id]
                time_diff = now - last_info["last_time"]
                last_author = last_info["last_author_id"]
                if time_diff >= timedelta(hours=1) and last_author != user.id:
                    await ach_cog.unlock_achievement(user, "midnight_monologue", channel)
            else:
                await ach_cog.unlock_achievement(user, "midnight_monologue", channel)

        self.channel_activity[channel_id] = {
            "last_time": now,
            "last_author_id": user.id
        }

        # おそよう
        if now.hour >= 13 and any(kw in content.lower() for kw in self.greeting_keywords):
            if self.osoyou_logs.get(user.id) != today:
                self.osoyou_logs[user.id] = today
                await ach_cog.unlock_achievement(user, "osoyou", channel)

        # エナカス
        if any(kw in content for kw in self.energy_keywords):
            if user.id not in self.energy_logs:
                self.energy_logs[user.id] = []
            self.energy_logs[user.id] = [t for t in self.energy_logs[user.id] if now - t < timedelta(minutes=3)]
            self.energy_logs[user.id].append(now)
            if len(self.energy_logs[user.id]) >= 2:
                await ach_cog.unlock_achievement(user, "energy_addict", channel)

        # 酒カス
        if now.hour >= 22 and any(kw in content for kw in self.alcohol_keywords):
            if user.id not in self.alcohol_logs:
                self.alcohol_logs[user.id] = []
            self.alcohol_logs[user.id] = [t for t in self.alcohol_logs[user.id] if now - t < timedelta(minutes=3)]
            self.alcohol_logs[user.id].append(now)
            if len(self.alcohol_logs[user.id]) >= 2:
                await ach_cog.unlock_achievement(user, "no_alcohol_ii", channel)

        # ── 画像から追加された隠し実績の判定群 ──
        if self.bot.user in message.mentions:
            await ach_cog.unlock_achievement(user, "minecraft_suru", channel)

        if "限界を超えた先にある不屈の精神" in content:
            await ach_cog.unlock_achievement(user, "tasogare_shoukei", channel)

        if "ｺﾝｽｨｰﾔwwﾚｯwﾄｩwwﾊwﾘｰwwﾃﾞｨwwwｲwﾃﾞｨwwkﾄwｴwﾗwwwｺｰｽﾞｨﾝwwwﾊﾟwwwﾃﾞｨwwｱwﾒｲwwwﾃﾞｨwwｼｭ↑wｶﾞｰwｺﾝﾌﾙｰｧwwwwﾚｯwwﾃｨwwwﾊwﾒｲｯwwwﾃｨwwwﾙｰﾝwwwﾔwwﾒwﾃﾞｨwｸﾗｷﾓwwwｲﾝwwﾅﾅｧ↑wwｲwwﾄwｷｨｨ↑↑ww" in content:  
            await ach_cog.unlock_achievement(user, "folern_kanzen", channel)

        async with self.bot.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_total_messages (user_id, count) VALUES ($1, 1)
                ON CONFLICT (user_id) DO UPDATE SET count = user_total_messages.count + 1
                """,
                user.id
            )
            total_msgs = await conn.fetchval(
                "SELECT count FROM user_total_messages WHERE user_id = $1", user.id
            )
        if total_msgs >= 10000:
            await ach_cog.unlock_achievement(user, "tutorial_finish", channel)

        async with self.bot.db.acquire() as conn:
            last_msg_time = await conn.fetchval(
                "SELECT last_sent FROM user_last_message WHERE user_id = $1", user.id
            )
            if last_msg_time:
                if now - last_msg_time >= timedelta(days=7):
                    await ach_cog.unlock_achievement(user, "ohisashiburi", channel)
            await conn.execute(
                """
                INSERT INTO user_last_message (user_id, last_sent) VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET last_sent = $2
                """,
                user.id, now
            )

        if content.replace(" ", "") in ["↑↓↑↓←→←→BA", "上下左右BA", "↑↓↑↓←→←→バ", "上下左右バ"]:
            await ach_cog.unlock_achievement(user, "not_a_game", channel)

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

        # 59: いいね (👍リアクション)
        if str(payload.emoji) == "👍":
            await ach_cog.unlock_achievement(member, "good_reaction", channel)

        async with self.bot.db.acquire() as conn:
            # 標準絵文字・カスタム絵文字両方を絵文字カウンターに集計
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