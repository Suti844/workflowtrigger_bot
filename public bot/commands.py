import discord
import requests
import sqlite3
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from publicbot_main import bot
from helper_functions import get_server_settings, update_server_settings

# === Slash Commands Route Registration === #

@bot.tree.command(name="wssetup", description="Setup Github workflow and Minecraft server targets")
@app_commands.describe(
    owner="GitHub username", 
    repo="GitHub repository (default=mcserverstarter)", 
    workflow_file="GitHub workflow file (default=main.yml)", 
    github_token="GitHub personal access token",
    git_branch="Target Git Branch (e.g., main, Asmp)",
    panel_server_name="Exact name of the server on the Seedloaf panel (e.g., Mafia)"
)
async def wssetup(
    interaction: discord.Interaction, 
    owner: str = None, 
    repo: str = None, 
    workflow_file: str = None, 
    github_token: str = None,
    git_branch: str = None,
    panel_server_name: str = None
):
    sid = interaction.guild_id
    if sid is None:
        return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)
    
    update_server_settings(sid,
        owner=owner,
        repo=repo,
        workflow_file=workflow_file,
        github_token=github_token,
        git_branch=git_branch,
        panel_server_name=panel_server_name
    )
    await interaction.response.send_message("✅ GitHub workflow and server panel settings updated.", ephemeral=True)

@bot.tree.command(name="botsetup", description="Setup bot limits")
@app_commands.describe(notify_channel="Notification channel", max_uses_per_day="Daily usage limit", cooldown_time="Cooldown in sec")
async def botsetup(interaction: discord.Interaction, notify_channel: discord.TextChannel = None, max_uses_per_day: int = None, cooldown_time: int = None):
    sid = interaction.guild_id
    if sid is None:
        return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)
    
    update_server_settings(sid,
        notify_channel=notify_channel.id if notify_channel else None,
        max_uses_per_day=max_uses_per_day,
        cooldown_time=cooldown_time
    )
    await interaction.response.send_message("✅ Bot settings updated.", ephemeral=True)

@bot.tree.command(name="run_mc", description="Trigger a GitHub Actions workflow to start the configured MC server")
@app_commands.describe(
    action="Choose whether to start or stop the world panel target"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Start Server", value="true"),
    app_commands.Choice(name="Stop Server", value="false")
])
async def run_mc(interaction: discord.Interaction, action: app_commands.Choice[str] = None):
    sid = interaction.guild_id
    uid = interaction.user.id
    if sid is None:
        return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)

    settings = get_server_settings(sid)
    if not settings:
        return await interaction.response.send_message("⚠️ Server settings not configured.", ephemeral=True)

    _, owner, repo, workflow_file, token, notify_channel, max_uses, cooldown, git_branch, panel_server_name = settings

    if not panel_server_name:
        return await interaction.response.send_message("❌ Error: No panel server name configured for this Discord server.", ephemeral=True)

    start_or_stop_val = action.value if action else "true"
    action_label = "START" if start_or_stop_val == "true" else "STOP"

    db = sqlite3.connect("bot_data.db")
    cursor = db.cursor()

    cursor.execute("SELECT uses, last_used FROM user_usage WHERE server_id = ? AND user_id = ?", (sid, uid))
    row = cursor.fetchone()
    now = datetime.utcnow().timestamp()

    if row:
        uses, last_used = row
        if uses >= max_uses:
            db.close()
            return await interaction.response.send_message("🚫 Daily usage limit reached.", ephemeral=True)
        if now - last_used < cooldown:
            remaining = int(cooldown - (now - last_used))
            db.close()
            return await interaction.response.send_message(f"⏳ Cooldown! Wait {remaining} sec.", ephemeral=True)
    else:
        uses, last_used = 0, 0

    await interaction.response.defer(ephemeral=True)

    url = f"https://github.com{owner}/{repo}/actions/workflows/{workflow_file}/dispatches"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    
    data = {
        "ref": git_branch,  
        "inputs": {
            "start_or_stop": start_or_stop_val,
            "use_session_cache": "true",
            "server_name": panel_server_name  
        }
    }

    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 204:
        if row:
            cursor.execute("UPDATE user_usage SET uses = ?, last_used = ? WHERE server_id = ? AND user_id = ?", (uses+1, now, sid, uid))
        else:
            cursor.execute("INSERT INTO user_usage (server_id, user_id, uses, last_used) VALUES (?, ?, ?, ?)", (sid, uid, 1, now))
        db.commit()
        db.close()

        await interaction.followup.send(f"✅ Workflow dispatch request for **{action_label}** sent successfully!", ephemeral=True)
        
        channel = bot.get_channel(notify_channel)
        if channel:
            try:
                await channel.send(f"🚀 {interaction.user.mention} requested a **{action_label}** event for the server.")
            except Exception:
                pass
    else:
        db.close()
        await interaction.followup.send(f"❌ Failed: {res.text}", ephemeral=True)

@bot.tree.command(name="show_settings")
async def show_settings(interaction: discord.Interaction):
    sid = interaction.guild_id
    settings = get_server_settings(sid)
    if not settings:
        return await interaction.response.send_message("⚠️ Server not set up yet.", ephemeral=True)

    _, owner, repo, workflow_file, token, notify_channel, max_uses, cooldown, git_branch, panel_server_name = settings
    notify_channel_display = f"<#{notify_channel}>" if notify_channel else "`None`"
    masked_token = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "Not Set"
    
    await interaction.response.send_message(
        f"📋 **Current Server Settings**\n"
        f" Owner: `{owner}`\n Repo: `{repo}`\n Workflow: `{workflow_file}`\n"
        f" Git Branch Target: `{git_branch}`\n"
        f" Panel Server Target Name: `{panel_server_name}`\n"
        f" Token: `{masked_token}`\n"
        f" Notify Channel: {notify_channel_display}\n"
        f" Max Uses/Day: `{max_uses}`\n⏱ Cooldown: `{cooldown} sec`",
        ephemeral=True
    )

@bot.tree.command(name="users_usage")
async def users_usage(interaction: discord.Interaction):
    sid = interaction.guild_id
    db = sqlite3.connect("bot_data.db")
    cursor = db.cursor()
    cursor.execute("SELECT user_id, uses FROM user_usage WHERE server_id = ?", (sid,))
    rows = cursor.fetchall()
    db.close()
    if not rows:
        return await interaction.response.send_message("No usage data.", ephemeral=True)
    result = "\n".join([f"<@{uid}>: {uses}" for uid, uses in rows])
    await interaction.response.send_message(f"📊 Usage Stats:\n{result}", ephemeral=True)

@bot.tree.command(name="reset_usage")
async def reset_usage(interaction: discord.Interaction):
    sid = interaction.guild_id
    db = sqlite3.connect("bot_data.db")
    cursor = db.cursor()
    cursor.execute("DELETE FROM user_usage WHERE server_id = ?", (sid,))
    db.commit()
    db.close()
    await interaction.response.send_message("🔄 Usage stats reset.", ephemeral=True)

# === Új parancs a beragadt duplikációk letörlésére === #
@bot.command()
@commands.is_owner()  
async def clearsync(ctx):
    progress_msg = await ctx.send("🧹 Régi parancsok törlése és tiszta szinkronizáció indítása...")
    try:
        # 1. Teljesen kiürítjük a Discord parancstárhelyét
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        
        # 2. Újra hozzáadjuk a friss, jelszó nélküli parancsokat
        # Mivel a commands.py-ban vagyunk, az importok már betöltötték a parancsokat a fenti dekorátorokkal
        synced_commands = await bot.tree.sync()
        
        await progress_msg.edit(content=f"✨ Sikeres tisztítás! A duplikációk eltűntek. **{len(synced_commands)}** parancs maradt tisztán.")
    except Exception as e:
        await progress_msg.edit(content=f"❌ Hiba a tisztítás során: `{e}`")
