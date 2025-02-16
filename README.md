# 🚀 Reforger Admin Tracker Bot

A **Discord bot** that tracks **online admins** across multiple Reforger servers using the **BattleMetrics API**. The bot allows admins to **register their Reforger ID**, **automatically detects online admins**, and **updates a Discord embed** with server details.

---

## 🔧 Features
✅ **Tracks Admins in Reforger Servers** - Uses BattleMetrics API to detect admins and update a Discord embed.  
✅ **Automatic Role-Based Removal** - Removes admins from the database if their required role is lost.  
✅ **Slash Command to Register IDs** - Admins can register their **Reforger ID** via `/addmyid`.  
✅ **Database Storage** - Admins' Discord IDs & Reforger IDs are stored in **MySQL/MariaDB**.  
✅ **Real-Time Discord Embed Updates** - Shows online admins, server names, and player counts.  
✅ **Bot Status Updates** - Displays the number of online admins as the bot's **Discord status**.  
✅ **Admin Database Query** - Allows authorized users to **query the database** with `/printdb`.  

---

## ⚙️ Setup & Installation

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

SERVER_1=31707876
SERVER_2=31707887
SERVER_3=31707886
SERVER_4=31707874
SERVER_5=31490334
SERVER_6=31517967
SERVER_7=31490831
SERVER_8=31569933
SERVER_9=31879399

ADMIN_FLAG="4e540ea0-03bc-11ed-a13f-a5c325391c93"
```

### 4️⃣ Start the Bot
```sh
python3 main.py
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

---

## ⚠️ Troubleshooting

- **Bot not responding to commands?**  
  - Make sure the bot **has permission to read and send messages** in the target channel.  
  - Ensure the bot **has "Use Slash Commands" permission** in your server settings.

- **Admins not showing up as online?**  
  - Verify that the **Reforger IDs are correctly registered**.  
  - Ensure **BattleMetrics API key** is **valid and has access** to fetch player data.

- **Database not updating?**  
  - Check if the **MySQL database is running** and credentials in `.env` are correct.  

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Contributors

- **[Your Name]** - Developer & Maintainer  
- **[Your Team/Guild Name]** - Support & Testing  

---

Now, you're ready to use the **Reforger Admin Tracker Bot**! 🚀
