# cogs/achievement.py
import discord
from discord.ext import commands
from discord import app_commands
from achievements_config import ACHIEVEMENTS

class AchievementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def unlock_achievement(self, member: discord.Member, achievement_id: str, channel: discord.TextChannel):
        """実績を解除する共通メソッド（すでに解除済みの場合はスルーし、初解除なら通知する）"""
        if achievement_id not in ACHIEVEMENTS:
            return

        async with self.bot.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                member.id, achievement_id
            )
            if row:
                return  # 解除済み

            await conn.execute(
                "INSERT INTO user_achievements (user_id, achievement_id) VALUES ($1, $2)",
                member.id, achievement_id
            )

        # 解除時の通知メッセージ
        ach_info = ACHIEVEMENTS[achievement_id]
        embed = discord.Embed(
            title=f"実績解除「{ach_info['name']}」",
            description=f"{member.mention} が解除しました",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)

        # 隠し実績（全解除系）の連鎖解除判定
        await self.check_meta_achievements(member, channel)

    async def check_meta_achievements(self, member: discord.Member, channel: discord.TextChannel):
        """全解除系（全実績解除？、負けました）の条件を満たしているかチェック"""
        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT achievement_id FROM user_achievements WHERE user_id = $1",
                member.id
            )
        unlocked_ids = {r["achievement_id"] for r in rows}

        normal_ach_ids = {aid for aid, ach in ACHIEVEMENTS.items() if not ach.get("is_hidden", False)}
        all_ach_ids = set(ACHIEVEMENTS.keys())

        # 1. 「全実績解除？」 (通常実績をすべて解除)
        if normal_ach_ids.issubset(unlocked_ids) and "all_unlock_q" not in unlocked_ids:
            await self.unlock_achievement(member, "all_unlock_q", channel)

        # 2. 「負けました」 (隠し含む全実績を解除)
        if all_ach_ids.issubset(unlocked_ids) and "you_lose" not in unlocked_ids:
            await self.unlock_achievement(member, "you_lose", channel)

    # ── コマンド定義 ──

    @app_commands.command(name="check", description="指定したユーザー（または自分）の進捗と解除済み実績一覧を確認します")
    @app_commands.describe(user="確認したいユーザー（省略した場合は自分になります）")
    async def check_progress(self, interaction: discord.Interaction, user: discord.Member = None):
        target_user = user or interaction.user

        normal_achievements = {aid for aid, ach in ACHIEVEMENTS.items() if not ach.get("is_hidden", False)}
        total_normal_count = len(normal_achievements)

        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT achievement_id FROM user_achievements WHERE user_id = $1",
                target_user.id
            )
        unlocked_ids = {row["achievement_id"] for row in rows}

        unlocked_normal_count = len(unlocked_ids.intersection(normal_achievements))
        unlocked_hidden_count = len(unlocked_ids - normal_achievements)

        # 解除済み実績リストの作成（隠し実績は未解除なら表示しない）
        desc_list = []
        for aid, ach in ACHIEVEMENTS.items():
            if ach.get("is_hidden", False) and aid not in unlocked_ids:
                continue
            if aid in unlocked_ids:
                desc_list.append(f"✅ **{ach['name']}** - {ach['description']}")

        embed = discord.Embed(
            title=f"📊 {target_user.display_name} さんの実績情報",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # 進捗状況
        embed.add_field(
            name="進捗状況（通常実績）",
            value=f"**{unlocked_normal_count} / {total_normal_count}** 達成",
            inline=False
        )
        
        if unlocked_hidden_count > 0:
            embed.add_field(
                name="🔒 隠し実績の解除数",
                value=f"{unlocked_hidden_count} 個解除済み",
                inline=False
            )

        # 解除済み一覧の表示
        if desc_list:
            embed.add_field(
                name="📜 解除済み実績一覧",
                value="\n".join(desc_list),
                inline=False
            )
        else:
            embed.add_field(
                name="📜 解除済み実績一覧",
                value="現在解除している実績はありません。",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ranking", description="サーバー内の実績解除数ランキングを表示します")
    async def achievement_ranking(self, interaction: discord.Interaction):
        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, COUNT(achievement_id) as count 
                FROM user_achievements 
                GROUP BY user_id 
                ORDER BY count DESC 
                LIMIT 10
                """
            )

        if not rows:
            await interaction.response.send_message("まだ誰も実績を解除していません！")
            return

        desc_lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            rank_icon = medals[i] if i < 3 else f"`#{i+1}`"
            user_id = row["user_id"]
            count = row["count"]
            
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"ID: {user_id}"
            
            desc_lines.append(f"{rank_icon} **{name}** : **{count}個** 解除")

        embed = discord.Embed(
            title="🏆 実績解除数ランキング TOP 10",
            description="\n".join(desc_lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="admin_give", description="【管理者用】指定したユーザーに実績を付与、または【ボットオーナー限定】で剥奪します")
    @app_commands.describe(
        action="付与する(give)か、剥奪する(take)かを選んでください",
        user="対象のユーザー",
        achievement_id="実績のID（例: not_admin, buy_anger など）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="付与 (give)", value="give"),
        app_commands.Choice(name="剥奪 (take)", value="take")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_give(self, interaction: discord.Interaction, action: str, user: discord.Member, achievement_id: str):
        if achievement_id not in ACHIEVEMENTS:
            await interaction.response.send_message(f"エラー: `{achievement_id}` という実績IDは存在しません。", ephemeral=True)
            return

        # 剥奪 (take) の場合はボットオーナー本人かどうかを厳密にチェック
        if action == "take":
            app_info = await self.bot.application_info()
            if interaction.user.id != app_info.owner.id:
                await interaction.response.send_message("❌ エラー: 実績の「剥奪」はボットのオーナー（あなた）しか実行できません。", ephemeral=True)
                return

        async with self.bot.db.acquire() as conn:
            if action == "give":
                row = await conn.fetchrow(
                    "SELECT 1 FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                    user.id, achievement_id
                )
                if row:
                    await interaction.response.send_message(f"{user.mention} はすでに `{achievement_id}` を解除しています。", ephemeral=True)
                    return
                
                await conn.execute(
                    "INSERT INTO user_achievements (user_id, achievement_id) VALUES ($1, $2)",
                    user.id, achievement_id
                )
                await interaction.response.send_message(f"✅ {user.mention} に実績 `{achievement_id}` (`{ACHIEVEMENTS[achievement_id]['name']}`) を付与しました！", ephemeral=True)
            
            elif action == "take":
                result = await conn.execute(
                    "DELETE FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                    user.id, achievement_id
                )
                if result == "DELETE 0":
                    await interaction.response.send_message(f"{user.mention} はその実績を所持していません。", ephemeral=True)
                    return
                
                await interaction.response.send_message(f"🗑️ {user.mention} から実績 `{achievement_id}` を剥奪しました。", ephemeral=True)

    @app_commands.command(name="all_check_url", description="実績管理スプレッドシートのURLを表示します")
    async def all_check_url(self, interaction: discord.Interaction):
        SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/10BCeT24d6KaHDrio1jtdVooZoRr-V80XfWJXdr0X7bM/edit?usp=drivesdk"
        
        embed = discord.Embed(
            title="🔗 実績スプレッドシート",
            description=f"進捗や一覧を確認できるスプレッドシートはこちらです：\n[スプレッドシートを開く]({SPREADSHEET_URL})",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AchievementCog(bot))