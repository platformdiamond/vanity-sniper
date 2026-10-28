import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import os

# ==================== CONFIG (use environment variables) ====================
TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
REQUIRED_STATUS = os.getenv("REQUIRED_STATUS", ".gg/GRBQmsGABC free cheatz and toolz")
REQUIRED_MINUTES = int(os.getenv("REQUIRED_MINUTES", "5"))
# ===========================================================================

intents = discord.Intents.default()
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

tracking = {}  # {user_id: datetime}


def get_custom_status(member: discord.Member) -> str | None:
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity):
            return activity.name
    return None


def has_required_status(member: discord.Member) -> bool:
    status = get_custom_status(member)
    if not status:
        return False
    return REQUIRED_STATUS.lower() in status.lower()


async def give_role(member: discord.Member):
    role = member.guild.get_role(ROLE_ID)
    if role and role not in member.roles:
        try:
            await member.add_roles(role, reason="Vanity status held for required time")
            print(f"[+] Gave role to {member} ({member.id})")
        except Exception as e:
            print(f"[!] Failed to give role to {member}: {e}")


async def remove_role(member: discord.Member):
    role = member.guild.get_role(ROLE_ID)
    if role and role in member.roles:
        try:
            await member.remove_roles(role, reason="Vanity status removed")
            print(f"[-] Removed role from {member} ({member.id})")
        except Exception as e:
            print(f"[!] Failed to remove role from {member}: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} | Vanity Sniper online")
    print(f"Watching for: {REQUIRED_STATUS}")
    print(f"Required time: {REQUIRED_MINUTES} minutes")
    check_statuses.start()


@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if after.guild is None or after.guild.id != GUILD_ID:
        return
    if after.bot:
        return

    user_id = after.id
    has_it = has_required_status(after)

    if has_it:
        if user_id not in tracking:
            tracking[user_id] = datetime.utcnow()
            print(f"[~] Started tracking {after}")
    else:
        if user_id in tracking:
            del tracking[user_id]
            print(f"[~] Stopped tracking {after}")
        await remove_role(after)


@tasks.loop(seconds=30)
async def check_statuses():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    now = datetime.utcnow()
    to_remove = []

    for user_id, start_time in list(tracking.items()):
        member = guild.get_member(user_id)
        if not member:
            to_remove.append(user_id)
            continue

        if not has_required_status(member):
            to_remove.append(user_id)
            await remove_role(member)
            continue

        if now - start_time >= timedelta(minutes=REQUIRED_MINUTES):
            await give_role(member)

    for uid in to_remove:
        tracking.pop(uid, None)


@check_statuses.before_loop
async def before_check():
    await bot.wait_until_ready()


if not TOKEN or not GUILD_ID or not ROLE_ID:
    print("Missing TOKEN, GUILD_ID or ROLE_ID environment variables!")
else:
    bot.run(TOKEN)
