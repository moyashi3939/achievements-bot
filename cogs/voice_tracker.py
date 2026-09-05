# cogs/voice_tracker.py
import discord
from discord.ext import commands
from datetime import datetime

class VoiceTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_sessions = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        now = datetime.now()

        # VC参加時
        if before.channel is None and after.channel is not None:
            self.voice_sessions[member.id] = {
                'time': now, 
                'mute': after.self_mute or after.mute
            }
            
            # 19番：「深夜の語り部」 (深夜0時以降〜朝4時までにVC参加)
            if 0 <= now.hour < 4:
                ach_cog = self.bot.get_cog("AchievementCog")
                if ach_cog:
                    ch = after.channel.guild.system_channel or (after.channel.guild.text_channels[0] if after.channel.guild.text_channels else None)
                    if ch:
                        await ach_cog.unlock_achievement(member, "midnight_talker", ch)

        # VC退出時
        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_sessions:
                session = self.voice_sessions.pop(member.id)
                duration = int((now - session['time']).total_seconds())
                guild = after.channel.guild

                # 5番：「主食はマイク」 (累計24時間用データベース加算)
                await self.add_voice_time(member, duration, guild)

                ach_cog = self.bot.get_cog("AchievementCog")
                if ach_cog:
                    ch = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                    if ch:
                        # 24番：「サイレントサポーター」 (ミュートのまま1時間=3600秒VC接続)
                        if session['mute'] and duration >= 3600:
                            await ach_cog.unlock_achievement(member, "silent_supporter", ch)

                        # 32番：「あなた暇なの？」 (連続接続24時間 = 86400秒以上)
                        if duration >= 86400:
                            await ach_cog.unlock_achievement(member, "you_free", ch)

    async def add_voice_time(self, member: discord.Member, duration: int, guild: discord.Guild):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_voice_time (user_id, total_seconds) VALUES ($1, $2)
                ON CONFLICT (user_id) 
                DO UPDATE SET total_seconds = user_voice_time.total_seconds + $2
                """,
                member.id, duration
            )
            total = await conn.fetchval(
                "SELECT total_seconds FROM user_voice_time WHERE user_id = $1",
                member.id
            )

        # 5番：「主食はマイク」 (累計24時間 = 86400秒)
        if total >= 86400:
            ach_cog = self.bot.get_cog("AchievementCog")
            if ach_cog:
                ch = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if ch:
                    await ach_cog.unlock_achievement(member, "staple_is_mic", ch)

async def setup(bot):
    await bot.add_cog(VoiceTrackerCog(bot))