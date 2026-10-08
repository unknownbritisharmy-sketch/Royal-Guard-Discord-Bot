# Royal Guard Discord Bot

A Royal Guard-inspired Discord bot template for a Roblox British Army-style community.

This repository is a clean, production-ready starter that you can customize to the exact command list and role names used on your Discord server. It is designed to stay online 24/7 when hosted on a cloud service and to support moderation, verification, role assignment, and server management commands.

Features:
- 24/7-ready Discord bot
- Prefix-based commands
- Moderation: warn, kick, ban, unban, mute, unmute, clear
- Server utilities: ping, status, uptime, help
- Verification / auto-role support
- Logs to a configured channel
- Owner-only commands

Important:
- This is a Royal Guard-inspired bot template, not a direct copy of another Discord server's proprietary bot or command set.
- You should replace the role IDs, command names, and server-specific logic with your own.

## Requirements
- Python 3.10+
- A Discord bot token
- A host provider like Render, Railway, Repl.it, or a VPS

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

4. Fill in your Discord token and server configuration in `.env`.

5. Run the bot:
   ```bash
   python bot.py
   ```

## Environment variables
- `DISCORD_TOKEN`: your bot token
- `BOT_PREFIX`: default command prefix (`!`)
- `OWNER_IDS`: comma-separated list of admin/owner user IDs
- `DEFAULT_ROLE_ID`: role assigned to new members
- `VERIFY_ROLE_ID`: role assigned after verification
- `LOG_CHANNEL_ID`: channel for bot logs

## 24/7 hosting
To keep the bot online when your computer or phone is offline, host it on a service such as:
- Render
- Railway
- Replit
- VPS / Raspberry Pi / Linux server

Recommended extra monitoring:
- UptimeRobot or a similar external uptime checker
- Auto-restart on crash using systemd or your hosting platform

## Customizing commands
Open `bot.py` and adapt the command names or role logic to your exact server layout.

## Example commands
- `!help`
- `!ping`
- `!status`
- `!verify`
- `!warn @User Spam`
- `!warnings @User`
- `!kick @User Reason`
- `!ban @User Reason`
- `!unban UserTag`
- `!mute @User Reason`
- `!unmute @User`
- `!clear 25`

## License
MIT
