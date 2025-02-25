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
import paramiko
import json

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
   
SFTP_SERVERS = []
for i in range(1, 10):  
    host = os.getenv(f"SFTP_HOST_{i}")
    port = os.getenv(f"SFTP_PORT_{i}")
    user = os.getenv(f"SFTP_USER_{i}")
    password = os.getenv(f"SFTP_PASS_{i}")
    filepath = os.getenv(f"SFTP_FILEPATH_{i}")

    if host and port and user and password and filepath:
        SFTP_SERVERS.append({
            "host": host,
            "port": int(port),
            "user": user,
            "password": password,
            "filepath": filepath
        })

print(f"[DEBUG] Loaded {len(SFTP_SERVERS)} SFTP servers for updates.")


@bot.tree.command(name="addmyid", description="Register your Reforger ID")
async def add_my_id(interaction: discord.Interaction, reforger_id: str):
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

   
    if len(reforger_id) != 36:
        await interaction.response.send_message("❌ Invalid Reforger ID. It must be **exactly 36 characters** long.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)
    role_id = str(REQUIRED_ROLE_ID)

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        cursor.execute("UPDATE admins SET reforger_id = %s WHERE discord_id = %s", (reforger_id, discord_id))
        msg = f"✅ **Updated** your Reforger ID to `{reforger_id}`."
    else:
        cursor.execute("INSERT INTO admins (discord_id, reforger_id, role_id) VALUES (%s, %s, %s)",
                       (discord_id, reforger_id, role_id))
        msg = f"✅ **Registered** your Reforger ID as `{reforger_id}`."

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

    
    try:
        manual_server9_entries = json.loads(os.getenv("SERVER_9_MANUAL_REFORGER_IDS", "{}"))
        print(f"[DEBUG] Loaded manual Server 9 overrides: {manual_server9_entries}")
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse SERVER_9_MANUAL_REFORGER_IDS: {e}")
        manual_server9_entries = {}

    for server_name, server_id in SERVERS.items():
        
        if not server_id.isdigit():  
            print(f"[DEBUG] Skipping non-numeric server ID: {server_id}")  
            continue

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

    
    for reforger_id, username in manual_server9_entries.items():
        online_admins[reforger_id] = "Server 9 Override"

    print(f"[DEBUG] Online Admins (including manual Server 9 overrides): {online_admins}")
    return online_admins



async def cleanup_removed_admins():
    """Scans for users who lost the required role and removes them from the database."""
    await bot.wait_until_ready()
    
    while True:
        print("[DEBUG] Scanning for role removes...")  

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT discord_id FROM admins")
        admins = cursor.fetchall()

        guild = bot.guilds[0]  

        for (discord_id,) in admins:
            member = guild.get_member(int(discord_id))
            if member:
                has_role = any(role.id == REQUIRED_ROLE_ID for role in member.roles)
                if not has_role:
                    print(f"[INFO] User {discord_id} had role removed, deleting from DB.")
                    cursor.execute("DELETE FROM admins WHERE discord_id = %s", (discord_id,))
                    conn.commit()

        cursor.close()
        conn.close()
        
        await asyncio.sleep(1800)  
        
async def update_missing_usernames():
    """Checks for missing Discord usernames in the database, updates them, and triggers an SFTP update if necessary."""
    await bot.wait_until_ready()

    while not bot.is_closed():
        print("[DEBUG] Checking for missing Discord usernames in the database...")

        conn = connect_db()
        cursor = conn.cursor()

        
        cursor.execute("SELECT discord_id FROM admins WHERE username IS NULL OR username = ''")
        missing_users = cursor.fetchall()

        if missing_users:
            print(f"[INFO] Found {len(missing_users)} users missing a Discord username. Attempting to update...")

        guild = bot.guilds[0]  
        updated = False  

        for (discord_id,) in missing_users:
            member = guild.get_member(int(discord_id))
            if member:
                username = member.name
                cursor.execute("UPDATE admins SET username = %s WHERE discord_id = %s", (username, discord_id))
                print(f"[INFO] Updated username for {discord_id} -> {username}")
                updated = True  

        conn.commit()
        cursor.close()
        conn.close()

       
        if updated:
            print("[INFO] Usernames updated. Triggering immediate SFTP update...")
            await schedule_sftp_updates()

        await asyncio.sleep(300)  


async def update_status():
    """Updates the bot's status with the number of online admins."""
    await bot.wait_until_ready()
    
    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            online_admins = await fetch_online_admins(session)
            total_admins = len(online_admins)

            if total_admins > 0:
                status_message = f"{total_admins} Admins Online"
            else:
                status_message = "No Admins Online"

            await bot.change_presence(activity=discord.Game(name=status_message))
            
            await asyncio.sleep(UPDATE_INTERVAL)
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
    bot.loop.create_task(schedule_sftp_updates())
    bot.loop.create_task(update_missing_usernames())
    print("[DEBUG] Scheduled SFTP update task started.")
    
@bot.tree.command(name="forceremove", description="Manually remove an admin from the database.")
async def force_remove(interaction: discord.Interaction, user: discord.Member):
    """Allows authorized users to remove an admin by mentioning them."""
    
    
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    discord_id = str(user.id)

    conn = connect_db()
    cursor = conn.cursor()

    
    cursor.execute("SELECT * FROM admins WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        cursor.execute("DELETE FROM admins WHERE discord_id = %s", (discord_id,))
        conn.commit()
        msg = f"✅ **Removed** {user.mention} from the database."
        print(f"[DEBUG] Removed {discord_id} ({user.name}) from the database.")
    else:
        msg = f"❌ {user.mention} is **not** in the database."
        print(f"[DEBUG] Attempted to remove {discord_id} ({user.name}), but they were not found.")

    cursor.close()
    conn.close()

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="forcedentry", description="Manually add an admin to the database.")
async def forced_entry(interaction: discord.Interaction, user: discord.Member, reforger_id: str):
    """Allows authorized users to manually add admins by Discord mention and Reforger ID."""
    
    
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    discord_id = str(user.id)
    username = user.name
    role_id = str(REQUIRED_ROLE_ID)

    conn = connect_db()
    cursor = conn.cursor()

   
    cursor.execute("SELECT * FROM admins WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        cursor.execute("UPDATE admins SET reforger_id = %s, username = %s WHERE discord_id = %s", 
                       (reforger_id, username, discord_id))
        msg = f"✅ **Updated** {user.mention}'s Reforger ID to `{reforger_id}`."
        print(f"[DEBUG] Updated {discord_id} ({username}) with Reforger ID: {reforger_id}")
    else:
        cursor.execute("INSERT INTO admins (discord_id, username, reforger_id, role_id) VALUES (%s, %s, %s, %s)",
                       (discord_id, username, reforger_id, role_id))
        msg = f"✅ **Added** {user.mention} with Reforger ID `{reforger_id}`."
        print(f"[DEBUG] Added {discord_id} ({username}) to the database with Reforger ID: {reforger_id}")

    conn.commit()
    cursor.close()
    conn.close()

    await interaction.response.send_message(msg, ephemeral=True)
    

@bot.tree.command(name="printdb", description="Print all registered admins from the database.")
async def print_db(interaction: discord.Interaction):
    """Restricts the command to users with the required role and prints the admin database."""
    
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, username, reforger_id FROM admins")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    if not admins:
        await interaction.response.send_message("📭 No admins found in the database.", ephemeral=True)
        return

    embed = discord.Embed(title="Registered Admins", color=discord.Color.green())

    
    admin_count = 0
    admin_text = ""
    
    for discord_id, username, reforger_id in admins:
        user = bot.get_user(int(discord_id))
        display_name = user.name if user else username
        admin_text += f"**{display_name}** - 🆔 {discord_id} | 🎮 {reforger_id}\n"
        admin_count += 1

       
        if admin_count == 25:
            embed.add_field(name="Admins List", value=admin_text, inline=False)
            admin_text = ""
            admin_count = 0

    if admin_text:
        embed.add_field(name="Admins List", value=admin_text, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)
    print(f"[DEBUG] Printed {len(admins)} admins from the database.")

    
async def schedule_sftp_updates():
    """Schedules periodic SFTP updates with the exported database data."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT reforger_id, username FROM admins")
        admins = cursor.fetchall()
        cursor.close()
        conn.close()

        if admins:
            
            admin_dict = {"admins": {reforger_id: (username if username else "null") for reforger_id, username in admins}}
            json_output = json.dumps(admin_dict, indent=4)

            print("[DEBUG] Running scheduled SFTP update...")
            await update_sftp_files(json_output)

        await asyncio.sleep(18000)  

async def update_sftp_files(json_data):
    """Writes the exported database JSON to remote SFTP servers while preserving the full config file."""

    
    try:
        manual_server9_ids = json.loads(os.getenv("SERVER_9_MANUAL_REFORGER_IDS", "{}"))
        print(f"[DEBUG] Loaded manual Server 9 overrides: {manual_server9_ids}")
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse SERVER_9_MANUAL_REFORGER_IDS: {e}")
        manual_server9_ids = {}

    
    try:
        admin_dict = json.loads(json_data) 
        admin_dict["admins"].update(manual_server9_ids) 
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to process admin JSON data: {e}")
        return

    for server in SFTP_SERVERS:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server["host"],
                port=server["port"],
                username=server["user"],
                password=server["password"]
            )

            sftp = ssh.open_sftp()
            remote_file_path = server["filepath"]

            
            try:
                with sftp.file(remote_file_path, "r") as f:
                    existing_data = f.read().decode("utf-8")
                    config_data = json.loads(existing_data)
            except (IOError, json.JSONDecodeError) as e:
                print(f"[ERROR] Failed to read existing config on {server['host']}: {e}")
                config_data = {}  

            
            config_data["admins"] = admin_dict["admins"]

            
            with sftp.file(remote_file_path, "w") as f:
                f.write(json.dumps(config_data, indent=4))

            sftp.close()
            ssh.close()
            print(f"[SUCCESS] Updated SFTP config on {server['host']} at {remote_file_path}")

        except Exception as e:
            print(f"[ERROR] Failed to update {server['host']}: {e}")


bot.run(DISCORD_TOKEN)
