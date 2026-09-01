import os
import discord
from discord.app_commands.tree import CommandTree
from discord.ext import commands
from discord.ext.commands.bot import _default
from discord.utils import MISSING
from dotenv import load_dotenv
from database import create_db_pool

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

class AchievementBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.db = await create_db_pool(DATABASE_URL)

        await self.load_extension("cogs.achievemet")
        await self.load_extension("cogs.voice_tracker")
        await self.load_extension("cogs.message_tracker")

        await self.tree.sync()
        print("スラッシュコマンドを同期しました。")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        print("エラー: DISCORD_TOKEN が環境変数に設定されていません。")
    else:
        bot = AchievementBot()
        bot.run(TOKEN)