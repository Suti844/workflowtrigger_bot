import sqlite3
import discord

def get_db_connection():
    return sqlite3.connect("bot_data.db")

def get_server_settings(server_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM server_settings WHERE server_id = ?", (server_id,))
    row = cursor.fetchone()
    db.close()
    return row

def update_server_settings(server_id, **kwargs):
    db = get_db_connection()
    cursor = db.cursor()
    current = get_server_settings(server_id)
    
    if current:
        for key, value in kwargs.items():
            if value is not None:  
                cursor.execute(f"UPDATE server_settings SET {key} = ? WHERE server_id = ?", (value, server_id))
    else:
        # Default initialization templates setup for new guilds 
        cursor.execute("""
            INSERT INTO server_settings (
                server_id, owner, repo, workflow_file, github_token, notify_channel, 
                max_uses_per_day, cooldown_time, git_branch, panel_server_name
            ) VALUES (?, '', 'mcserverstarter', 'main.yml', '', 0, 3, 600, 'main', '')
        """, (server_id,))
        
        # Populate custom overrides recursively
        for key, value in kwargs.items():
            if value is not None:
                cursor.execute(f"UPDATE server_settings SET {key} = ? WHERE server_id = ?", (value, server_id))
                
    db.commit()
    db.close()

# 🔄 ADDED THIS FUNCTION BACK TO FIX YOUR IMPORT ERROR
async def update_presence(bot):
    """
    Updates the bot's custom status presence.
    """
    try:
        activity = discord.Activity(type=discord.ActivityType.watching, name="MC Servers")
        await bot.change_presence(activity=activity)
        print("🎮 Bot status presence updated successfully.")
    except Exception as e:
        print(f"⚠️ Failed to update presence: {e}")
