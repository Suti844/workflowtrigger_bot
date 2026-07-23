import discord
import sqlite3
from discord.ext import commands

# === SQLite initialization === #
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()

# Updated schema tracking the explicit branches and hidden password panel tags
cursor.execute('''CREATE TABLE IF NOT EXISTS server_settings (
    server_id INTEGER PRIMARY KEY,
    owner TEXT,
    repo TEXT,
    workflow_file TEXT,
    github_token TEXT,
    notify_channel INTEGER,
    max_uses_per_day INTEGER,
    cooldown_time INTEGER,
    git_branch TEXT,
    panel_server_name TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS user_usage (
    server_id INTEGER,
    user_id INTEGER,
    uses INTEGER,
    last_used REAL,
    PRIMARY KEY (server_id, user_id)
)''')
db.commit()

# === Bot Bootstrap Init === #
DISCORD_TOKEN = "mycutetokenuwu"  # Replace with your actual token
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Import modular listeners/commands once global bot is set up
import helper_functions
import events
import commands as bot_commands

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} and commands synchronized globally.")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
