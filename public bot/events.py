import discord
from discord import File
from helper_functions import update_presence, update_server_settings, get_server_settings

def setup(bot, cursor, db):

    @bot.event
    async def on_ready():
        await bot.tree.sync()
        print(f"✅ Logged in as {bot.user}")
        await update_presence(bot)

    @bot.event
    async def on_guild_join(guild: discord.Guild):
        await update_presence(bot)
        update_server_settings(cursor, db, guild.id)
        channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if channel:
            intro_msg = (
                "**👋 Thanks for adding me!**\n"
                "You need to setup this https://github.com/dibope/mcserverstarter \n"
                "Read the README file above link \n"
                "Use `/wssetup` to connect the GitHub workflow\n"
                "Use `/botsetup` to configure usage limits and notify log channel\n"
                "There is `/stop_mc` too so disable it if u don't want users to stop server\n\n"
            )

            settings = get_server_settings(cursor, guild.id)
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
                await channel.send(final_message)
                )
            else:
                await channel.send(intro_msg)

    @bot.event
    async def on_guild_remove(guild):
        await update_presence(bot)
