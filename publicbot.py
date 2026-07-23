import os
import discord
import sqlite3
from discord.ext import commands

# === SQLite inicializálás === #
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()

# Frissített séma az egyedi ágak és a rejtett panelszerver nevek követéséhez
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

# === Bot Indítás és Beállítások === #
# Környezeti változóból olvassa be a tokent a Render felületéről
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Javítja a "Privileged message content intent is missing" hibát

bot = commands.Bot(command_prefix="!", intents=intents)

# Moduláris fájlok importálása, miután a globális bot objektum létrejött
import helper_functions
import events
import commands as bot_commands

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bejelentkezve mint {bot.user}! A parancsok sikeresen szinkronizálva a Discorddal.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ HIBA: A DISCORD_TOKEN környezeti változó nincs beállítva a Render felületén!")
    else:
        bot.run(DISCORD_TOKEN)
