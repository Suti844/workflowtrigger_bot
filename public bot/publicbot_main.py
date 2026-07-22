import discord
import sqlite3
from discord.ext import commands
import commands as bot_commands
import events as bot_events
import os

# === SQLite setup === #
db = sqlite3.connect("./bot_data.db")
cursor = db.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS server_settings (
    server_id INTEGER PRIMARY KEY,
    owner TEXT,
    repo TEXT,
    workflow_file TEXT,
    github_token TEXT,
    notify_channel INTEGER,
    max_uses_per_day INTEGER,
    cooldown_time INTEGER,
    use_session_cache INTEGER DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS user_usage (
    server_id INTEGER,
    user_id INTEGER,
    uses INTEGER,
    last_used REAL,
    uses_stop INTEGER,
    last_used_stop REAL,
    PRIMARY KEY (server_id, user_id)
)''')

db.commit()

# === Bot Setup === #

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Register commands and events
bot_commands.setup(bot, cursor, db)
bot_events.setup(bot, cursor, db)

# === Run Bot === #
bot.run(DISCORD_TOKEN)
