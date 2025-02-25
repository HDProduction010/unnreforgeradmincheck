# UnnReforger Admin Tracker Bot

A **Discord bot** that tracks **online admins** across multiple Arma Reforger servers using the **BattleMetrics API**. The bot allows admins to **register their Reforger ID**, **automatically detect online admins**, and **update a Discord embed** with server details.

Additionally, it **syncs admin data** to multiple **remote servers** via **SFTP** to ensure that admin lists are up to date across all managed servers.

---

## **Setup & Configuration**

### **1️⃣ Install Dependencies**
Ensure you have **Python 3.10+** and install the required dependencies:

```bash
pip install -r requirements.txt
```

### **2️⃣ Configure the `.env` File**
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

# BattleMetrics Server IDs
SERVER_1=BM_SERVER_ID
SERVER_2=BM_SERVER_ID
...
SERVER_9=BM_SERVER_ID

# Manual Overrides for Server 9 Admin List
SERVER_9_MANUAL_REFORGER_IDS={"REPLACEME_GUID":"AdminName", "REPLACEME_GUID2":"AnotherAdmin"}

# SFTP Configurations for Remote Server Updates
SFTP_HOST_1=YOUR_SFTP_HOST
SFTP_PORT_1=YOUR_SFTP_PORT
SFTP_USER_1=YOUR_SFTP_USERNAME
SFTP_PASS_1=YOUR_SFTP_PASSWORD
SFTP_FILEPATH_1=/path/to/config.json

# Repeat for up to 9 servers
SFTP_HOST_2=...
```

---

## **Slash Commands**

| Command                     | Description |
|-----------------------------|-------------|
| `/addmyid <ReforgerID>`     | **Registers** your Reforger ID in the database. |
| `/printdb`                  | **Prints all registered admins** (only accessible to authorized users). |
| `/exportdb`                 | **Exports the database** in JSON format and triggers an SFTP update. |
| `/forceremove @User`        | **Manually removes an admin** from the database. |
| `/forcedentry @User <ReforgerID>` | **Manually adds an admin** to the database. |
| `/addserver9override <ReforgerID>` | **Manually adds a Reforger ID override** for Server 9. |

---

## **How It Works**

### **🔹 Admin Registration**
- Admins **register** their Reforger ID using `/addmyid <ReforgerID>`, linking it to their Discord account.
- The bot **stores the data** in a MySQL database.

### **🔹 Automatic Admin Tracking**
- The bot **periodically scans servers** using the **BattleMetrics API**.
- It **compares player Reforger IDs** with stored admin IDs to check **who is online**.

### **🔹 Discord Embed & Status Updates**
- The bot updates a **Discord embed message** with:
  - **Server names**
  - **Player counts**
  - **Currently online admins (tagged in Discord)**
- The **bot's status** dynamically updates to show the **total number of connected admins**.

### **🔹 Auto-Removal of Inactive Admins**
- The bot **checks if admins still have the required role**.
- If an admin **loses their role**, they are **automatically removed** from the database.

### **🔹 SFTP Server Synchronization**
- The bot **exports the admin database** as JSON and **uploads it** via **SFTP** to multiple remote servers.
- **Overrides for Server 9** can be added via the `.env` file.

### **🔹 Fix for Missing Discord Usernames**
- If an admin's **Discord username** is missing from the database, the bot **automatically attempts to update it** every **5 minutes**.
- If a username remains missing, the bot **adds "null" in JSON format** to prevent breaking the exported config files.

### **🔹 Validation for Reforger IDs**
- The bot **validates Reforger IDs** before adding them:
  - ✅ Must be a valid length.
  - ❌ If too short or too long, the bot **rejects the entry**.

---

## **Debugging & Logging**
- The bot **logs important events** to **help with debugging**:
  - ✅ When an admin registers, updates, or is removed.
  - ✅ When server status updates occur.
  - ✅ When **SFTP uploads** succeed or fail.
  - ✅ When invalid JSON or database issues occur.
  - ✅ When an admin ID is missing or incorrectly formatted.
  - ✅ When the bot **fixes missing usernames**.

---

## **License**
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## **Future Improvements**
✅ Improve error handling for SFTP failures.  
✅ Add **role-based permissions** for slash commands.  
✅ Implement **auto-fix for missing Discord usernames**.  
✅ Prevent **invalid Reforger IDs** from being added.  
⬜️ Support **multiple Discord servers** (future).  

---
