import os
import requests
import json
from datetime import datetime
from typing import List, Optional

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")
OWNER_IDS = [int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]
DEFAULT_ROLE_ID = int(os.getenv("DEFAULT_ROLE_ID", "0") or 0)
VERIFY_ROLE_ID = int(os.getenv("VERIFY_ROLE_ID", "0") or 0)
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or 0)

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    help_command=None,
)

bot.start_time = datetime.utcnow()
warnings_store = {}
verified_users = {}

ROBLOX_API_BASE = "https://users.roblox.com/v1/users"
ROBLOX_USERNAME_API = "https://api.roblox.com/users/get-by-username"


def get_warning_list(user_id: int) -> List[str]:
    return warnings_store.setdefault(user_id, [])


async def log_action(guild: discord.Guild, message: str):
    if LOG_CHANNEL_ID == 0:
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel is not None and isinstance(channel, discord.TextChannel):
        await channel.send(message)


async def get_or_create_muted_role(guild: discord.Guild) -> discord.Role:
    muted_role = discord.utils.get(guild.roles, name="Muted")
    if muted_role is None:
        muted_role = await guild.create_role(name="Muted", reason="Created automatically for mute command")
    return muted_role


def get_roblox_user_id(username: str) -> Optional[int]:
    """
    Fetches the Roblox user ID from a username.
    Returns the user ID or None if not found.
    """
    try:
        response = requests.get(f"{ROBLOX_USERNAME_API}?username={username}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("Id")
    except Exception as e:
        print(f"Error fetching Roblox user ID for {username}: {e}")
    return None


def get_roblox_user_info(user_id: int) -> Optional[dict]:
    """
    Fetches detailed Roblox user information.
    Returns user data or None if not found.
    """
    try:
        response = requests.get(f"{ROBLOX_API_BASE}/{user_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching Roblox user info for ID {user_id}: {e}")
    return None


def get_roblox_user_friends_count(user_id: int) -> Optional[int]:
    """
    Fetches the number of friends a Roblox user has.
    Helps prevent bot accounts and throwaway accounts from verifying.
    """
    try:
        response = requests.get(f"https://friends.roblox.com/v1/users/{user_id}/friends/count", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("count", 0)
    except Exception as e:
        print(f"Error fetching friend count for Roblox user {user_id}: {e}")
    return None


@bot.event
async def on_ready():
    print(f"Royal Guard Bot is online: {bot.user.name}#{bot.user.discriminator} ({bot.user.id})")
    print(f"Prefix: {PREFIX}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{PREFIX}help | Royal Guard",
        )
    )
    # Load verified users from storage (if you want to persist across restarts)
    try:
        if os.path.exists("verified_users.json"):
            with open("verified_users.json", "r") as f:
                global verified_users
                verified_users = json.load(f)
                print(f"Loaded {len(verified_users)} verified users from storage.")
    except Exception as e:
        print(f"Could not load verified users: {e}")


@bot.event
async def on_member_join(member: discord.Member):
    if DEFAULT_ROLE_ID:
        role = member.guild.get_role(DEFAULT_ROLE_ID)
        if role:
            await member.add_roles(role, reason="Default role assigned on join")

    await log_action(member.guild, f"✅ {member.mention} joined the server.")


@bot.event
async def on_member_remove(member: discord.Member):
    await log_action(member.guild, f"👋 {member.mention} left the server.")


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="Royal Guard Command List",
        description="Commands available to all members and staff.",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="General",
        value="`!help` `!ping` `!status` `!uptime` `!verify`",
        inline=False,
    )
    embed.add_field(
        name="Roblox Verification",
        value="`!robloxverify <username>` `!myroblox` `!unverify`",
        inline=False,
    )
    embed.add_field(
        name="Moderation",
        value="`!warn @user reason` `!warnings @user` `!kick @user reason` `!ban @user reason` `!unban username#tag` `!mute @user reason` `!unmute @user` `!clear 25`",
        inline=False,
    )
    embed.add_field(
        name="Owner",
        value="`!shutdown` `!restart`",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Bot latency: {round(bot.latency * 1000)}ms")


@bot.command(name="status")
async def status(ctx):
    await ctx.send(f"✅ Royal Guard Bot is online and ready for duty. Prefix: `{PREFIX}`")


@bot.command(name="uptime")
async def uptime(ctx):
    current_time = datetime.utcnow()
    delta = current_time - bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f"⏰ Uptime: {hours}h {minutes}m {seconds}s")


@bot.command(name="robloxverify")
async def roblox_verify(ctx, username: str):
    """
    Verify a Discord user with their Roblox account.
    Usage: !robloxverify <roblox_username>
    """
    # Normalize the username (remove spaces, lowercase)
    username = username.strip()
    
    # Get Roblox user ID from username
    user_id = get_roblox_user_id(username)
    if user_id is None:
        await ctx.send(f"❌ Could not find a Roblox account with the username `{username}`. Please check the spelling.")
        return

    # Get user info
    user_info = get_roblox_user_info(user_id)
    if user_info is None:
        await ctx.send(f"❌ Could not retrieve information for Roblox user `{username}`.")
        return

    # Get friend count (optional security check)
    friend_count = get_roblox_user_friends_count(user_id)
    
    # Optional: Reject accounts with very few friends (anti-bot measure)
    if friend_count is not None and friend_count < 1:
        await ctx.send(f"❌ The Roblox account `{username}` has no friends. Please use an established account with at least 1 friend.")
        return

    # Store verification
    verified_users[str(ctx.author.id)] = {
        "discord_id": ctx.author.id,
        "discord_username": str(ctx.author),
        "roblox_id": user_id,
        "roblox_username": user_info.get("name", username),
        "verified_at": datetime.utcnow().isoformat(),
        "friend_count": friend_count,
    }

    # Save to file for persistence
    try:
        with open("verified_users.json", "w") as f:
            json.dump(verified_users, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save verified users to file: {e}")

    # Assign verification role if set
    if VERIFY_ROLE_ID:
        role = ctx.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await ctx.author.add_roles(role, reason="Roblox verification completed")

    embed = discord.Embed(
        title="✅ Roblox Verification Successful",
        description=f"You have been verified!",
        color=discord.Color.green(),
    )
    embed.add_field(name="Discord", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Roblox Username", value=f"{user_info.get('name', username)}", inline=True)
    embed.add_field(name="Roblox ID", value=f"{user_id}", inline=True)
    if friend_count is not None:
        embed.add_field(name="Friends", value=f"{friend_count}", inline=True)
    embed.set_thumbnail(url=user_info.get("thumbnailUrl", ""))

    await ctx.send(embed=embed)
    await log_action(
        ctx.guild,
        f"✅ {ctx.author.mention} verified Roblox account: **{user_info.get('name', username)}** (ID: {user_id})",
    )


@bot.command(name="myroblox")
async def my_roblox(ctx):
    """
    Show your verified Roblox account information.
    """
    discord_id = str(ctx.author.id)
    if discord_id not in verified_users:
        await ctx.send(f"❌ You are not verified. Use `{PREFIX}robloxverify <username>` to verify your Roblox account.")
        return

    user_data = verified_users[discord_id]
    roblox_id = user_data.get("roblox_id")
    roblox_username = user_data.get("roblox_username")
    verified_at = user_data.get("verified_at")
    friend_count = user_data.get("friend_count")

    embed = discord.Embed(
        title="Your Roblox Account",
        description=f"Verified on {verified_at}",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Discord", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Roblox Username", value=f"{roblox_username}", inline=True)
    embed.add_field(name="Roblox ID", value=f"{roblox_id}", inline=True)
    if friend_count is not None:
        embed.add_field(name="Friends", value=f"{friend_count}", inline=True)

    await ctx.send(embed=embed)


@bot.command(name="unverify")
async def unverify(ctx):
    """
    Remove your Roblox verification.
    """
    discord_id = str(ctx.author.id)
    if discord_id not in verified_users:
        await ctx.send(f"❌ You are not verified.")
        return

    del verified_users[discord_id]

    # Save to file
    try:
        with open("verified_users.json", "w") as f:
            json.dump(verified_users, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save verified users to file: {e}")

    # Remove verification role if set
    if VERIFY_ROLE_ID:
        role = ctx.guild.get_role(VERIFY_ROLE_ID)
        if role and role in ctx.author.roles:
            await ctx.author.remove_roles(role, reason="Unverified by user")

    await ctx.send("✅ Your Roblox verification has been removed.")
    await log_action(ctx.guild, f"❌ {ctx.author.mention} unverified their Roblox account.")


@bot.command(name="verify")
async def verify(ctx):
    await ctx.send(f"✅ {ctx.author.mention} has been verified.")


@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.bot:
        await ctx.send("❌ You cannot warn a bot.")
        return

    warnings = get_warning_list(member.id)
    warnings.append(f"{ctx.author.name}: {reason}")

    await ctx.send(f"⚠️ {member.mention} has been warned for: `{reason}`")
    await log_action(ctx.guild, f"⚠️ {member.mention} was warned by {ctx.author.mention}: {reason}")


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    entries = get_warning_list(member.id)
    if not entries:
        await ctx.send(f"📋 {member.mention} has no warnings.")
        return

    text = "\n".join(f"- {entry}" for entry in entries)
    await ctx.send(f"📋 Warning history for {member.mention}:\n{text}")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} was kicked. Reason: `{reason}`")
    await log_action(ctx.guild, f"👢 {member.mention} was kicked by {ctx.author.mention}: {reason}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔒 {member.mention} was banned. Reason: `{reason}`")
    await log_action(ctx.guild, f"🔒 {member.mention} was banned by {ctx.author.mention}: {reason}")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, username: str):
    try:
        member = await commands.UserConverter().convert(ctx, username)
    except commands.BadArgument:
        await ctx.send("❌ Could not find that user. Use the full username and tag: `Name#1234`")
        return

    await ctx.guild.unban(member, reason="Unbanned by staff command")
    await ctx.send(f"✅ {member.mention} was unbanned.")
    await log_action(ctx.guild, f"✅ {member.mention} was unbanned by {ctx.author.mention}.")


@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    muted_role = await get_or_create_muted_role(ctx.guild)
    if muted_role in member.roles:
        await ctx.send(f"⚠️ {member.mention} is already muted.")
        return

    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f"🔇 {member.mention} has been muted. Reason: `{reason}`")
    await log_action(ctx.guild, f"🔇 {member.mention} was muted by {ctx.author.mention}: {reason}")


@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role is None:
        await ctx.send("⚠️ There is no Muted role in this server.")
        return

    if muted_role not in member.roles:
        await ctx.send(f"⚠️ {member.mention} is not muted.")
        return

    await member.remove_roles(muted_role, reason="Unmute command")
    await ctx.send(f"🔊 {member.mention} has been unmuted.")
    await log_action(ctx.guild, f"🔊 {member.mention} was unmuted by {ctx.author.mention}.")


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    if amount < 1:
        await ctx.send("❌ Please provide a number greater than zero.")
        return

    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Cleared {amount} messages.", delete_after=3)


@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role is None:
        await ctx.send(f"❌ I could not find a role named `{role_name}`.")
        return

    if role in member.roles:
        await ctx.send(f"⚠️ {member.mention} already has the `{role_name}` role.")
        return

    await member.add_roles(role, reason=f"Role assigned via {ctx.command.name}")
    await ctx.send(f"✅ Added `{role_name}` to {member.mention}.")


@bot.command(name="shutdown")
async def shutdown(ctx):
    if ctx.author.id not in OWNER_IDS:
        await ctx.send("❌ You are not allowed to use this command.")
        return

    await ctx.send("⚠️ Shutting down the bot...")
    await bot.close()


@bot.command(name="restart")
async def restart(ctx):
    if ctx.author.id not in OWNER_IDS:
        await ctx.send("❌ You are not allowed to use this command.")
        return

    await ctx.send("🔄 Restarting the bot...")
    await bot.close()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument. Use `{PREFIX}help` for command usage.")
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ I could not find that member.")
        return

    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use that command.")
        return

    if isinstance(error, commands.CommandNotFound):
        return

    print(f"Command error: {error}")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN is missing. Add it to your .env file.")
    bot.run(TOKEN)
