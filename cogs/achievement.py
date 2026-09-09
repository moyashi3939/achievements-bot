# cogs/achievement.py
import discord
from discord.ext import commands
from discord import app_commands
from achievements_config import ACHIEVEMENTS

class AchievementPaginationView(discord.ui.View):
    def __init__(self, embed_list, interaction: discord.Interaction):
        super().__init__(timeout=180)
        self.embed_list = embed_list
        self.current_page = 0
        self.interaction_user = interaction.user

    async def update_message(self, interaction: discord.Interaction):
        embed = self.embed_list[self.current_page]
        embed.set_footer(text=f"ページ {self.current_page + 1} / {len(self.embed_list)}")
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embed_list) - 1

    @discord.ui.button(label="◀ 前へ", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("他のユーザーのページ操作はできません。", ephemeral=True)
            return
        self.current_page -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="次へ ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("他のユーザーのページ操作はできません。", ephemeral=True)
            return
        self.current_page += 1
        await self.update_message(interaction)

class AchievementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def unlock_achievement(self, member: discord.Member, achievement_id: str, channel: discord.TextChannel):
        """実績を解除する共通メソッド"""
        if achievement_id not in ACHIEVEMENTS:
            return

        async with self.bot.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                member.id, achievement_id
            )
            if row:
                return

            await conn.execute(
                "INSERT INTO user_achievements (user_id, achievement_id) VALUES ($1, $2)",
                member.id, achievement_id
            )

        # 解除時の通知メッセージ（3行目に条件を追加）
        ach_info = ACHIEVEMENTS[achievement_id]
        embed = discord.Embed(
            title=f"実績解除「{ach_info['name']}」",
            description=f"{member.mention} が解除しました\n\n**解除条件:** {ach_info['description']}",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)

        await self.check_meta_achievements(member, channel)

    async def check_meta_achievements(self, member: discord.Member, channel: discord.TextChannel):
        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT achievement_id FROM user_achievements WHERE user_id = $1",
                member.id
            )
        unlocked_ids = {r["achievement_id"] for r in rows}

        normal_ach_ids = {aid for aid, ach in ACHIEVEMENTS.items() if not ach.get("is_hidden", False)}
        all_ach_ids = set(ACHIEVEMENTS.keys())

        if normal_ach_ids.issubset(unlocked_ids) and "all_unlock_q" not in unlocked_ids:
            await self.unlock_achievement(member, "all_unlock_q", channel)

        if all_ach_ids.issubset(unlocked_ids) and "you_lose" not in unlocked_ids:
            await self.unlock_achievement(member, "you_lose", channel)

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

        desc_list = []
        for aid, ach in ACHIEVEMENTS.items():
            if ach.get("is_hidden", False) and aid not in unlocked_ids:
                continue
            if aid in unlocked_ids:
                desc_list.append(f"✅ **{ach['name']}** - {ach['description']}")

        # 1ページあたり5個に分割
        chunk_size = 5
        chunks = [desc_list[i:i + chunk_size] for i in range(0, len(desc_list), chunk_size)]
        if not chunks:
            chunks = [["現在解除している実績はありません。"]]

        embed_list = []
        for idx, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"📊 {target_user.display_name} さんの実績情報",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
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

            embed.add_field(
                name="📜 解除済み実績一覧",
                value="\n".join(chunk),
                inline=False
            )
            embed.set_footer(text=f"ページ {idx + 1} / {len(chunks)}")
            embed_list.append(embed)

        if len(embed_list) == 1:
            await interaction.response.send_message(embed=embed_list[0])
        else:
            view = AchievementPaginationView(embed_list, interaction)
            view.update_buttons()
            await interaction.response.send_message(embed=embed_list[0], view=view)

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

    @app_commands.command(name="admin_give", description="【オーナー限定】指定したユーザーに実績を付与、または剥奪します")
    @app_commands.describe(
        action="付与する(give)か、剥奪する(take)か",
        user="対象のユーザー",
        achievement_id="実績のID"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="付与 (give)", value="give"),
        app_commands.Choice(name="剥奪 (take)", value="take")
    ])
    async def admin_give(self, interaction: discord.Interaction, action: str, user: discord.Member, achievement_id: str):
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            await interaction.response.send_message("❌ エラー: このコマンドはボットのオーナーしか実行できません。", ephemeral=True)
            return

        if achievement_id not in ACHIEVEMENTS:
            await interaction.response.send_message(f"エラー: `{achievement_id}` という実績IDは存在しません。", ephemeral=True)
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
                await interaction.response.send_message(f"✅ {user.mention} に実績 `{achievement_id}` を付与しました！", ephemeral=True)
            
            elif action == "take":
                result = await conn.execute(
                    "DELETE FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                    user.id, achievement_id
                )
                if result == "DELETE 0":
                    await interaction.response.send_message(f"{user.mention} はその実績を所持していません。", ephemeral=True)
                    return
                
                await interaction.response.send_message(f"🗑️ {user.mention} から実績 `{achievement_id}` を剥奪しました。", ephemeral=True)

    @app_commands.command(name="admin_reset_db", description="【オーナー限定】DBに保存されている実績データをすべて削除します")
    async def admin_reset_db(self, interaction: discord.Interaction):
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            await interaction.response.send_message("❌ エラー: このコマンドはボットのオーナーしか実行できません。", ephemeral=True)
            return

        async with self.bot.db.acquire() as conn:
            await conn.execute("DELETE FROM user_achievements")
            # トラッキング用のカウントデータも一緒に初期化したい場合は追加可能ですが、まずは実績データのみ削除します

        embed = discord.Embed(
            title="⚠️ DBデータ初期化完了",
            description="`user_achievements` テーブルのすべての実績データを削除しました。",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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