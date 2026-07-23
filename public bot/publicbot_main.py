import os
import sys
import discord
import sqlite3
import threading
from flask import Flask
from discord.ext import commands

# Force Python to look inside the spaced folder path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# === SQLite initialization === #
db = sqlite3.connect("bot_data.db")
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

# === Production Flask Instance for Gunicorn Gateway (CRITICAL FIX) === #
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Bot interface is online and healthy!", 200

# === Bot Framework Initialization === #
intents = discord.Intents.default()
intents.message_content = True  # Resolves privileged intent warning logs

bot = commands.Bot(command_prefix="!", intents=intents)

# Modular imports run safely now that sys.path is updated
import helper_functions
import events
import commands as bot_commands

# Background target execution loop to unblock async threads
def run_discord_bot():
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        print("❌ CRITICAL ERROR: The 'DISCORD_TOKEN' environment variable is missing on Render!")
    else:
        bot.run(DISCORD_TOKEN.strip())

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Connected! Logged in as {bot.user} and commands synchronized globally.")

# Spawns Discord bot connection asynchronously right behind the Gunicorn deployment gateway
threading.Thread(target=run_discord_bot, daemon=True).start()

# This allows local execution fallback debugging without Gunicorn mapping
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
