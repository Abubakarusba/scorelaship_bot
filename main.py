import json
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# -----------------------------
# CONFIGURATION
# -----------------------------
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"     # <-- keep EXACT name
GROUP_ID = -1001234567890             # <-- your Telegram group ID
DATA_FILE = "data.json"               # <-- JSON database

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------
# JSON DATABASE FUNCTIONS
# -----------------------------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("data.json not found — creating new file.")
        return {"opportunities": []}
    except json.JSONDecodeError:
        logger.error("JSON CORRUPTION ERROR — FIXING FILE…")
        return {"opportunities": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        logger.info("Data saved successfully.")
    except Exception as e:
        logger.error(f"ERROR SAVING JSON: {e}")

# -----------------------------
# COMMAND: /add
# Add an opportunity manually.
# Example:
# /add Fully funded UK scholarship. Deadline Jan 3.
# -----------------------------
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = " ".join(context.args)

    if not message:
        await update.message.reply_text("❌ Usage: /add opportunity_text_here")
        return

    data = load_data()
    data["opportunities"].append(message)
    save_data(data)

    await update.message.reply_text("✅ Opportunity added successfully!")

# -----------------------------
# COMMAND: /list
# Shows all opportunities in JSON.
# -----------------------------
async def list_opps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    opps = data.get("opportunities", [])

    if not opps:
        await update.message.reply_text("📭 No opportunities yet.")
        return

    text = "📢 *Saved Opportunities:*\n\n"
    for i, opp in enumerate(opps, 1):
        text += f"{i}. {opp}\n\n"

    await update.message.reply_text(text)

# -----------------------------
# COMMAND: /nigeria
# You can modify this to filter tags later.
# -----------------------------
async def nigeria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    opps = data.get("opportunities", [])
    if not opps:
        await update.message.reply_text("🇳🇬 No Nigeria-specific opportunities yet.")
        return

    await update.message.reply_text("Here are the latest opportunities for Nigeria:")
    for opp in opps:
        await update.message.reply_text(opp)

# -----------------------------
# AUTOMATIC SCHEDULED POSTER
# Posts in your group DAILY.
# -----------------------------
async def scheduled_post(app):
    while True:
        data = load_data()
        opps = data.get("opportunities", [])

        if opps:
            msg = f"📢 *Daily Scholarship Update ({datetime.now().strftime('%Y-%m-%d')})*\n\n"
            msg += opps[-1]  # last added opportunity

            try:
                await app.bot.send_message(
                    chat_id=GROUP_ID,
                    text=msg,
                    parse_mode="Markdown"
                )
                logger.info("Auto message sent successfully.")
            except Exception as e:
                logger.error(f"FAILED to send auto post: {e}")

        await asyncio.sleep(24 * 60 * 60)  # wait 24 hours

# -----------------------------
# START COMMAND
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Your scholarship bot is active.\n\n"
        "Use /add to store opportunities.\n"
        "Use /list to view them.\n"
        "Use /nigeria to check Nigerian scholarships."
    )

# -----------------------------
# MAIN
# -----------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_opps))
    app.add_handler(CommandHandler("nigeria", nigeria))

    # Start scheduled posting
    asyncio.create_task(scheduled_post(app))

    logger.info("BOT RUNNING...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
