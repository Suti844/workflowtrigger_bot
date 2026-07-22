import discord
import requests
from discord import app_commands
from datetime import datetime
from helper_functions import get_server_settings, update_server_settings
from discord import File

def setup(bot, cursor, db):

    @bot.tree.command(name="wssetup", description="Setup Github workflow settings")
    @app_commands.describe(
        repo="GitHub repository(default=mcserverstarter)",
        workflow_file="GitHub workflow file(default=selenium.yml)",
        github_token="GitHub personal access token",
        use_session="store session to skip login and save time (sync ur repo in github unless its new)"
    )
    async def wssetup(interaction: discord.Interaction, repo: str = None, workflow_file: str = None, github_token: str = None, use_session: bool = None):
        sid = interaction.guild_id
        if sid is None:
            return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)
        username = None
        if github_token is not None:
            headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"}
            response = requests.get("https://api.github.com/user", headers=headers)
            if response.status_code == 200:
                username = response.json().get("login")
            else:
                embed = discord.Embed(description=f"❌ Invalid token, cannot fetch username: {response.text}", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                github_token = None
        update_server_settings(cursor, db, sid, owner=username, repo=repo, workflow_file=workflow_file, github_token=github_token, use_session_cache=use_session)
        await interaction.response.send_message("✅ GitHub workflow settings updated.", ephemeral=True)

    @bot.tree.command(name="botsetup", description="Setup bot settings like notify channel, max uses, cooldown time")
    @app_commands.describe(notify_channel="Notification channel", cooldown_time="Cooldown in sec (default = 600)")
    async def botsetup(interaction: discord.Interaction, notify_channel: discord.TextChannel = None, cooldown_time: int = None):
        sid = interaction.guild_id
        if sid is None:
            return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)
        update_server_settings(cursor, db, sid, notify_channel=notify_channel.id if notify_channel else None, cooldown_time=cooldown_time)
        await interaction.response.send_message("✅ Bot settings updated.", ephemeral=True)

    @bot.tree.command(name="start_mc", description="Trigger a GitHub Actions workflow to start the MC server")
    async def start_mc(interaction: discord.Interaction):
        sid = interaction.guild_id
        uid = interaction.user.id
        if sid is None:
            return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)

        settings = get_server_settings(cursor, sid)
        if not settings:
            return await interaction.response.send_message("⚠️ Server settings not configured.", ephemeral=True)

        _, owner, repo, workflow_file, token, notify_channel, max_uses, cooldown, use_session_cache = settings

        cursor.execute("SELECT uses, last_used FROM user_usage WHERE server_id = ? AND user_id = ?", (sid, uid))
        row = cursor.fetchone()
        now = datetime.utcnow().timestamp()

        if row:
            uses, last_used = row
            if now - last_used < cooldown:
                remaining = int(cooldown - (now - last_used))
                return await interaction.response.send_message(f"⏳ Cooldown! Wait {remaining} sec.", ephemeral=True)
        else:
            uses, last_used = 0, 0

        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            username = response.json().get("login")
            update_server_settings(cursor, db, sid, owner=username)
        else:
            embed = discord.Embed(description=f"❌ Invalid token, cannot fetch username: {response.text}", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        url = f"https://api.github.com/repos/{username}/{repo}/actions/workflows/{workflow_file}/dispatches"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        data = {"ref": "main"} if not use_session_cache else {"ref": "main", "inputs": {"use_session_cache": "true"}}

        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 204:
            if row:
                cursor.execute("UPDATE user_usage SET uses = ?, last_used = ? WHERE server_id = ? AND user_id = ?", (uses+1, now, sid, uid))
            else:
                cursor.execute("INSERT INTO user_usage (server_id, user_id, uses, last_used, uses_stop, last_used_stop) VALUES (?, ?, ?, ?, ?, ?)", (sid, uid, 1, now, 0, 0))
            db.commit()
            embed = discord.Embed(description="✅ Request sent\n Server will start in few minutes!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            channel = bot.get_channel(notify_channel)
            if channel:
                await channel.send(f"🚀 {interaction.user.mention} ran the MC workflow.")
        else:
            embed = discord.Embed(description=f"❌ Failed: {res.text}", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="stop_mc", description="Trigger a GitHub Actions workflow to stop the MC server")
    async def stop_mc(interaction: discord.Interaction):
        sid = interaction.guild_id
        uid = interaction.user.id
        if sid is None:
            return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)

        settings = get_server_settings(cursor, sid)
        if not settings:
            return await interaction.response.send_message("⚠️ Server settings not configured.", ephemeral=True)

        _, owner, repo, workflow_file, token, notify_channel, max_uses, cooldown, use_session_cache = settings

        cursor.execute("SELECT uses_stop, last_used_stop FROM user_usage WHERE server_id = ? AND user_id = ?", (sid, uid))
        row = cursor.fetchone()
        now = datetime.utcnow().timestamp()

        if row:
            uses, last_used = row
            if now - last_used < cooldown:
                remaining = int(cooldown - (now - last_used))
                return await interaction.response.send_message(f"⏳ Cooldown! Wait {remaining} sec.", ephemeral=True)
        else:
            uses, last_used = 0, 0

        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            username = response.json().get("login")
            update_server_settings(cursor, db, sid, owner=username)
        else:
            embed = discord.Embed(description=f"❌ Invalid token, cannot fetch username: {response.text}", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        url = f"https://api.github.com/repos/{username}/{repo}/actions/workflows/{workflow_file}/dispatches"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        if use_session_cache:
            data = {"ref": "main", "inputs": {"use_session_cache": "true", "start_or_stop": "false"}}
        else:
            data = {"ref": "main", "inputs": {"start_or_stop": "false"}}

        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 204:
            if row:
                cursor.execute("UPDATE user_usage SET uses_stop = ?, last_used_stop = ? WHERE server_id = ? AND user_id = ?", (uses+1, now, sid, uid))
            else:
                cursor.execute("INSERT INTO user_usage (server_id, user_id, uses, last_used, uses_stop, last_used_stop) VALUES (?, ?, ?, ?, ?, ?)", (sid, uid, 0, 0, 1, now))
            db.commit()
            embed = discord.Embed(description="✅ Request sent\n Server will stop in few minutes!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            channel = bot.get_channel(notify_channel)
            if channel:
                await channel.send(f"🚀 {interaction.user.mention} ran the MC workflow(stopworld).")
        else:
            description_embed = f"❌ Failed: {res.text}"
            if "inputs" in res.text:
                description_embed = f"❌ You need to sync or update repo to use this: {res.text}"
            embed = discord.Embed(description=description_embed, color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="users_usage")
    async def users_usage(interaction: discord.Interaction):
        sid = interaction.guild_id
        cursor.execute("SELECT user_id, uses, uses_stop FROM user_usage WHERE server_id = ?", (sid,))
        rows = cursor.fetchall()
        if not rows:
            return await interaction.response.send_message("No usage data.", ephemeral=True)
        result = "\n".join([f"<@{uid}>: starts:{uses}, stops:{uses_stop}" for uid, uses, uses_stop in rows])
        await interaction.response.send_message(f"📊 Usage Stats:\n{result}", ephemeral=True)

    @bot.tree.command(name="show_settings")
    async def show_settings(interaction: discord.Interaction):
        sid = interaction.guild_id
        settings = get_server_settings(cursor, sid)
        if not settings:
            return await interaction.response.send_message("⚠️ Server not set up yet.", ephemeral=True)

        _, owner, repo, workflow_file, token, notify_channel, max_uses, cooldown, use_session_cache = settings
        notify_channel_display = f"<#{notify_channel}>" if notify_channel else "`None`"
        await interaction.response.send_message(
            f" **Current Server Settings**\n"
            f" Owner: `{owner}`\n Repo: `{repo}`\n Workflow: `{workflow_file}`\n"
            f" Token: `{token[:4]}...{token[-4:]}`\n"
            f" Notify Channel: {notify_channel_display}\n"
            f" ⏱ Cooldown: `{cooldown} sec`\n"
            f" Using Session: {'`True`' if use_session_cache else '`False`'}",
            ephemeral=True
        )
    @bot.tree.command(name="help", description="Show setup instructions and current server settings")
    async def help_command(interaction: discord.Interaction):
        sid = interaction.guild_id
        if sid is None:
            return await interaction.response.send_message("🚫 Use this in a server.", ephemeral=True)

        intro_msg = (
            "**👋 Thanks for adding me!**\n"
            "You need to setup this https://github.com/dibope/mcserverstarter \n"
            "Read the README file above link \n"
            "Use `/wssetup` to connect the GitHub workflow\n"
            "Use `/botsetup` to configure usage limits and notify log channel\n"
            "There is `/stop_mc` too so disable it if u don't want users to stop server\n\n"
        )

        settings = get_server_settings(cursor, sid)
        if settings:
            _, owner, repo, workflow_file, token, notify_channel, max_uses, cooldown, use_session_cache = settings
            notify_channel_display = f"<#{notify_channel}>" if notify_channel else "`None`"

            settings_msg = (
                "You dont need to change Repo, Workflow file if you haven't edited the repo(even the name of repo too).\n"
                "Also Github username is fetched for you to check.\n\n"
                f" **Current Server Settings**\n"
                f" Owner(Github username): `{owner}`\n Repo: `{repo}`\n Workflow: `{workflow_file}`\n"
                f" Token: `{token[:4]}...{token[-4:]}`\n"
                f" Notify Channel: {notify_channel_display}\n"
                f" ⏱ Cooldown: `{cooldown} sec`\n"
                f" Using Session: {'`True`' if use_session_cache else '`False`'}"
            )

            final_message = intro_msg + settings_msg
            await interaction.response.send_message(
                final_message,
                ephemeral=True
        )
        else:
            await interaction.response.send_message(intro_msg, ephemeral=True)
