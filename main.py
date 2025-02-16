import discord
import os
import mysql.connector
import asyncio
import aiohttp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BATTLEMETRICS_TOKEN = os.getenv("BATTLEMETRICS_TOKEN")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
REQUIRED_ROLE_ID = int(os.getenv("REQUIRED_ROLE_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MESSAGE_ID = int(os.getenv("MESSAGE_ID"))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 360))
ADMIN_FLAG = os.getenv("ADMIN_FLAG", "4e540ea0-03bc-11ed-a13f-a5c325391c93")

SERVERS = {key: os.getenv(key) for key in os.environ if key.startswith("SERVER_")}

HEADERS = {
    "Authorization": f"Bearer {BATTLEMETRICS_TOKEN}",
    "Accept": "application/json"
}

def connect_db():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        collation="utf8mb4_general_ci"
    )

@bot.tree.command(name="addmyid", description="Register your Reforger ID")
async def add_my_id(interaction: discord.Interaction, reforger_id: str):
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)
    role_id = str(REQUIRED_ROLE_ID)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admins WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        cursor.execute("UPDATE admins SET reforger_id = %s WHERE discord_id = %s", (reforger_id, discord_id))
        msg = f":white_check_mark: Updated your Reforger ID to `{reforger_id}`."
    else:
        cursor.execute("INSERT INTO admins (discord_id, reforger_id, role_id) VALUES (%s, %s, %s)",
                       (discord_id, reforger_id, role_id))
        msg = f" Registered your Reforger ID as `{reforger_id}`."

    conn.commit()
    cursor.close()
    conn.close()

    await interaction.response.send_message(msg, ephemeral=True)

async def fetch_server_details(session):
    server_data = {}

    for server_name, server_id in SERVERS.items():
        url = f"https://api.battlemetrics.com/servers/{server_id}"
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                continue

            data = await response.json()
            name = data.get("data", {}).get("attributes", {}).get("name", "Unknown Server")
            player_count = data.get("data", {}).get("attributes", {}).get("players", 0)
            server_data[server_id] = {"name": name, "player_count": player_count}

    return server_data

async def fetch_online_admins(session):
    """Searches each server for all player Reforger UUIDs and checks against stored IDs."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, reforger_id FROM admins")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    online_admins = {}

    for server_name, server_id in SERVERS.items():
        url = f"https://api.battlemetrics.com/servers/{server_id}?include=identifier"
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                print(f"[ERROR] Failed to fetch players for server {server_id} | Status: {response.status}")
                continue

            data = await response.json()
            identifiers = {i["attributes"]["identifier"]: i["attributes"]["type"] for i in data.get("included", []) if i["type"] == "identifier"}

            for discord_id, reforger_id in admins:
                if reforger_id in identifiers and identifiers[reforger_id] == "reforgerUUID":
                    online_admins[discord_id] = server_id

    print(f"[DEBUG] Online Admins: {online_admins}")  # Debugging output
    return online_admins

async def cleanup_removed_admins():
    """Scans for users who lost the required role and removes them from the database."""
    await bot.wait_until_ready()
    
    while True:
        print("[DEBUG] Scanning for role removes...")  # ? Debug log

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT discord_id FROM admins")
        admins = cursor.fetchall()

        guild = bot.guilds[0]  # Assuming the bot is in only one server

        for (discord_id,) in admins:
            member = guild.get_member(int(discord_id))
            if member:
                has_role = any(role.id == REQUIRED_ROLE_ID for role in member.roles)
                if not has_role:
                    # ? Log the removal
                    print(f"[INFO] User {discord_id} had role removed, deleting from DB.")
                    
                    # ? Delete the full entry from the database
                    cursor.execute("DELETE FROM admins WHERE discord_id = %s", (discord_id,))
                    conn.commit()

        cursor.close()
        conn.close()
        
        await asyncio.sleep(1800)  # Check every 30 minutes
async def update_status():
    """Updates the bot's status with the number of online admins."""
    await bot.wait_until_ready()
    
    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            online_admins = await fetch_online_admins(session)
            total_admins = len(online_admins)

            if total_admins > 0:
                status_message = f":police_officer: {total_admins} Admins Online"
            else:
                status_message = "No Admins Online"

            await bot.change_presence(activity=discord.Game(name=status_message))
            
            await asyncio.sleep(UPDATE_INTERVAL)  # Update at the same interval as embed
async def update_embed():
    """Updates the Discord embed with all servers, player counts, and mentions online admins."""
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("[ERROR] Invalid channel ID")
        return

    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            server_details = await fetch_server_details(session)
            online_admins = await fetch_online_admins(session)

            total_admins = len(online_admins)
            embed = discord.Embed(
                title=f"Admin Status - {total_admins} Admins Online" if total_admins > 0 else "Admin Status - No Admins Online",
                color=discord.Color.blue()
            )

            est = pytz.timezone("America/New_York")
            now = datetime.now(est)

            for server_id, details in server_details.items():
                server_name = details.get("name", "Unknown Server")
                player_count = details.get("player_count", 0)

                admins_in_server = [
                    bot.get_user(int(discord_id)).mention
                    for discord_id, s_id in online_admins.items() if s_id == server_id
                ]

                embed.add_field(
                    name=f"{server_name} ({player_count} Players)",
                    value="\n".join(admins_in_server) if admins_in_server else "No admins online",
                    inline=False
                )

            embed.set_footer(text="Updated at")
            embed.timestamp = now

            try:
                message = await channel.fetch_message(MESSAGE_ID)
                await message.edit(content=None, embed=embed)
            except discord.NotFound:
                message = await channel.send(embed=embed)
                with open(".env", "a") as env_file:
                    env_file.write(f"\nMESSAGE_ID={message.id}")

            await asyncio.sleep(UPDATE_INTERVAL)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

    try:
        await bot.wait_until_ready()
        bot.tree.copy_global_to(guild=discord.Object(id=bot.guilds[0].id))
        await bot.tree.sync()
        print("? Slash commands synced successfully!")
    except Exception as e:
        print(f"? Failed to sync commands: {e}")

    bot.loop.create_task(update_embed())
    bot.loop.create_task(cleanup_removed_admins())
    bot.loop.create_task(update_status())

@bot.tree.command(name="printdb", description="Print all registered admins from the database.")
async def print_db(interaction: discord.Interaction):
    """Restricts the command to users with the required role and prints the admin database."""
    
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, reforger_id FROM admins")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    if not admins:
        await interaction.response.send_message("📭 No admins found in the database.", ephemeral=True)
        return

    embed = discord.Embed(title="Registered Admins", color=discord.Color.green())
    for discord_id, reforger_id in admins:
        user = bot.get_user(int(discord_id))
        username = user.name if user else f"Unknown ({discord_id})"
        embed.add_field(name=username, value=f"🆔 Discord: {discord_id}\n🎮 Reforger ID: {reforger_id}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(DISCORD_TOKEN)
