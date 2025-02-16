# 🚀 Reforger Admin Tracker Bot

A **Discord bot** that tracks **online admins** across multiple Reforger servers using the **BattleMetrics API**. The bot allows admins to **register their Reforger ID**, **automatically detects online admins**, and **updates a Discord embed** with server details.

---

### 3️⃣ Configure the `.env` File  
Create a **`.env`** file in the project directory and configure the following variables:

```
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
BATTLEMETRICS_TOKEN=YOUR_BATTLEMETRICS_API_KEY

MYSQL_HOST=your-mysql-host
MYSQL_USER=your-mysql-user
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=your-database-name

REQUIRED_ROLE_ID=DISCORD_ROLE_ID_FOR_ADMINS
CHANNEL_ID=DISCORD_CHANNEL_FOR_EMBED
MESSAGE_ID=DISCORD_MESSAGE_ID_TO_UPDATE
UPDATE_INTERVAL=360  # Time in seconds between updates

SERVER_1=789234 # BM Server IDs
....

```


---

## 📜 Commands

| Command        | Description |
|---------------|------------|
| `/addmyid <ReforgerID>` | **Registers** your Reforger ID in the database. |
| `/printdb` | **Prints all registered admins** (Only accessible to authorized users). |

---

## 🛠️ How It Works

1️⃣ **Admins Register**  
   - An admin uses `/addmyid <ReforgerID>` to link their Reforger ID to their Discord account.  

2️⃣ **Bot Scans Servers**  
   - The bot fetches player lists from **BattleMetrics** and checks for stored **Reforger IDs**.  

3️⃣ **Embed & Status Updates**  
   - The **Discord embed** updates every few minutes with:
     - **Server names**
     - **Player counts**
     - **Online admins (tagged in Discord)**
   - The **bot's status** updates to show the **number of connected admins**.

4️⃣ **Admins are Auto-Removed if Their Role is Lost**  
   - The bot **periodically checks** if an admin **still has the required role**.
   - If they **lost the role**, they are **removed from the database**.

5️⃣ **Authorized Users Can Query the Database**  
   - Using `/printdb`, **authorized users** can view all **stored admins** in an embed.

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

