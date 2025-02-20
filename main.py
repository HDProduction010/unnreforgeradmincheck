import discord
import os
import mysql.connector
import asyncio
import aiohttp
import json
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

async def ensure_db_fields():
    """Checks if the 'username' column exists and updates missing usernames."""
    conn = connect_db()
    cursor = conn.cursor()

    # Ensure 'username' column exists
    cursor.execute("SHOW COLUMNS FROM admins LIKE 'username'")
    result = cursor.fetchone()
    if not result:
        print("[INFO] Adding 'username' column to database.")
        cursor.execute("ALTER TABLE admins ADD COLUMN username VARCHAR(255) AFTER discord_id")
        conn.commit()

    # Update missing usernames
    cursor.execute("SELECT discord_id FROM admins WHERE username IS NULL OR username = ''")
    missing_users = cursor.fetchall()

    guild = bot.guilds[0]  # Assume bot is only in one guild
    for (discord_id,) in missing_users:
        member = guild.get_member(int(discord_id))
        if member:
            username = member.name
            cursor.execute("UPDATE admins SET username = %s WHERE discord_id = %s", (username, discord_id))
            print(f"[INFO] Updated missing username for {discord_id} -> {username}")

    conn.commit()
    cursor.close()
    conn.close()

@bot.tree.command(name="addmyid", description="Register your Reforger ID")
async def add_my_id(interaction: discord.Interaction, reforger_id: str):
    user_roles = [role.id for role in interaction.user.roles]
    if REQUIRED_ROLE_ID not in user_roles:
        await interaction.response.send_message("âŒ You do not have permission to use this command.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)
    username = interaction.user.name  # Get username dynamically
    role_id = str(REQUIRED_ROLE_ID)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admins WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        cursor.execute("UPDATE admins SET reforger_id = %s, username = %s WHERE discord_id = %s", 
                       (reforger_id, username, discord_id))
        msg = f"âœ… Updated your Reforger ID to `{reforger_id}`."
    else:
        cursor.execute("INSERT INTO admins (discord_id, username, reforger_id, role_id) VALUES (%s, %s, %s, %s)",
                       (discord_id, username, reforger_id, role_id))
        msg = f"âœ… Registered your Reforger ID as `{reforger_id}`."

    conn.commit()
    cursor.close()
    conn.close()

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="printdb", description="Print all registered admins from the database.")
async def print_db(interaction: discord.Interaction):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, username, reforger_id FROM admins")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    if not admins:
        await interaction.response.send_message("ðŸ“­ No admins found in the database.", ephemeral=True)
        return

    embed = discord.Embed(title="Registered Admins", color=discord.Color.green())

    for discord_id, username, reforger_id in admins[:25]:  # Discord limits embeds to 25 fields
        embed.add_field(name=username, value=f"ðŸ†” Discord: {discord_id}\nðŸŽ® Reforger ID: {reforger_id}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="exportdb", description="Export the admin database in JSON format.")
async def export_db(interaction: discord.Interaction):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT reforger_id, username FROM admins")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    if not admins:
        await interaction.response.send_message("ðŸ“­ No admins found in the database.", ephemeral=True)
        return

    admin_dict = {"admins": {reforger_id: username for reforger_id, username in admins}}
    json_output = json.dumps(admin_dict, indent=4)

    await interaction.response.send_message(f"```json\n{json_output}\n```", ephemeral=True)

async def cleanup_removed_admins():
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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

    try:
        await bot.wait_until_ready()
        await ensure_db_fields()  # Ensure database structure is correct
        bot.tree.copy_global_to(guild=discord.Object(id=bot.guilds[0].id))
        await bot.tree.sync()
        print("âœ… Slash commands synced successfully!")
    except Exception as e:
        print(f"âŒ Failed to sync commands: {e}")

    bot.loop.create_task(cleanup_removed_admins())

bot.run(DISCORD_TOKEN)
