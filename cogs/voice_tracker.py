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

        if before.channel is None and after.channel is not None:
            self.voice_sessions[member.id] = {'time': now, 'mute': after.self_mute or after.mute}
            
            if now.hour >= 0 and now.hour < 5:
                ach_cog = self.bot.get_cog("AchievementCog")
                if ach_cog:
                    ch = after.channel.guild.system_channel or (after.channel.guild.text_channels[0] if after.channel.guild.text_channels else None)
                    if ch:
                        await ach_cog.unlock_achievement(member, "midnight_talker", ch)

        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_sessions:
                session = self.voice_sessions.pop(member.id)
                duration = int((now - session['time']).total_seconds())
                await self.add_voice_time(member, duration, after.channel.guild)

                if session['mute'] and duration >= 3600:
                    ach_cog = self.bot.get_cog("AchievementCog")
                    if ach_cog:
                        ch = after.channel.guild.system_channel or (after.channel.guild.text_channels[0] if after.channel.guild.text_channels else None)
                        if ch:
                            await ach_cog.unlock_achievement(member, "silent_supporter", ch)

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

        if total >= 86400:  # 24時間
            ach_cog = self.bot.get_cog("AchievementCog")
            if ach_cog:
                ch = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if ch:
                    await ach_cog.unlock_achievement(member, "staple_is_mic", ch)

async def setup(bot):
    await bot.add_cog(VoiceTrackerCog(bot))