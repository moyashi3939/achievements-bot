# main.py
import discord
from discord.ext import commands
import os
import asyncpg
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

class AchievementBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)
        self.db = None

    async def setup_hook(self):
        # 1. PostgreSQL データベース接続プールを初期化
        try:
            self.db = await asyncpg.create_pool(DATABASE_URL)
            print("🚀 PostgreSQL データベースに接続しました。")
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")

        # 2. データベースのテーブル（初期テーブル）を作成・確認
        await self.init_db()

        # 3. 各 Cog の読み込み（スペルミスに注意！）
        extensions = [
            "cogs.achievement",
            "cogs.message_tracker",
            "cogs.voice_tracker"
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"📦 読み込み成功: {ext}")
            except Exception as e:
                print(f"❌ 読み込み失敗: {ext} (エラー: {e})")

        # 4. スラッシュコマンド（App Commands）をDiscordへ同期
        try:
            synced = await self.tree.sync()
            print(f"sync完了: {len(synced)} 個のコマンドを同期しました。")
        except Exception as e:
            print(f"❌ コマンド同期エラー: {e}")

    async def init_db(self):
        """必要なテーブルがなければ作成する"""
        async with self.db.acquire() as conn:
            # 実績解除管理テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id BIGINT,
                    achievement_id TEXT,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            # VC接続時間累計管理テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_voice_time (
                    user_id BIGINT PRIMARY KEY,
                    total_seconds BIGINT DEFAULT 0
                )
            """)
            # 絵文字使用回数累計テーブル（絵文字職人・21番用）
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_emoji_counts (
                    user_id BIGINT PRIMARY KEY,
                    count INT DEFAULT 0
                )
            """)
            # 他メンバーへのリアクション回数累計テーブル（共感の嵐・20番用）
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_reaction_counts (
                    user_id BIGINT PRIMARY KEY,
                    count INT DEFAULT 0
                )
            """)
        print("🛠️ データベースのテーブル初期化が完了しました。")

        async def on_ready(self):
          print(f"✨ ログイン完了: {self.user} (ID: {self.user.id})")

# ボットの起動
if __name__ == "__main__":
    bot = AchievementBot()
    bot.run(TOKEN)