#!/usr/bin/env python3
# ScoreLaship Hub AI — clean, stable, GROUP_ID from environment

import os
import json
import asyncio
from datetime import datetime, timedelta
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")  # <-- NOW READ FROM ENVIRONMENT
DATA_FILE = os.getenv("DATA_FILE", "data.json")

POST_HOUR = 8
POST_MINUTE = 30

FOOTER = (
    "\n\n🌐 Share to your friends"
    "\nJoin our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"
)

if not BOT_TOKEN:
    raise SystemExit("ERROR: BOT_TOKEN missing from environment!")

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------
# JSON DATA UTILS
# -----------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"opportunities": []}, f)

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read JSON: %s", e)
        return {"opportunities": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error("Failed to save JSON: %s", e)

# -----------------------------
# HELPERS
# -----------------------------
def filter_category(data, category):
    return [opp for opp in data.get("opportunities", []) if opp.get("category", "").lower() == category.lower()]

def format_opportunity(opp):
    return f"🎓 {opp.get('text', '')}{FOOTER}"

# -----------------------------
# COMMAND HANDLERS
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ScoreLaship Hub AI active.\n"
        "Commands:\n"
        "/list\n/nigeria\n/tech\n/international\n/getid"
    )

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type

    await update.message.reply_text(
        f"Chat ID: `{chat_id}`\nType: `{chat_type}`",
        parse_mode="Markdown"
    )

async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    opportunities = data.get("opportunities", [])

    if not opportunities:
        await update.message.reply_text("⚠️ No opportunities found.")
        return

    for opp in opportunities[:5]:
        await update.message.reply_text(format_opportunity(opp))

async def category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    data = load_data()
    opps = filter_category(data, category)

    if not opps:
        await update.message.reply_text(f"⚠️ No {category} opportunities available.")
        return

    for opp in opps[:5]:
        await update.message.reply_text(format_opportunity(opp))

async def nigeria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_cmd(update, context, "nigeria")

async def tech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_cmd(update, context, "tech")

async def international(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await category_cmd(update, context, "international")

# -----------------------------
# SCHEDULED POSTING
# -----------------------------
async def scheduled_post(app):
    while True:
        now = datetime.now()
        target = now.replace(hour=POST_HOUR, minute=POST_MINUTE, second=0, microsecond=0)

        if now > target:
            target += timedelta(days=1)

        await asyncio.sleep((target - now).total_seconds())

        logger.info("Running scheduled post...")

        if not GROUP_ID:
            logger.warning("GROUP_ID missing — skipping scheduled posting.")
            continue

        data = load_data()

        for cat in ["nigeria", "tech", "international"]:
            opps = filter_category(data, cat)

            for opp in opps:
                try:
                    await app.bot.send_message(GROUP_ID, format_opportunity(opp))
                    logger.info(f"Posted {cat} opportunity to group {GROUP_ID}")
                except Exception as e:
                    logger.error("Failed to send scheduled message: %s", e)

        await asyncio.sleep(60)

# -----------------------------
# MAIN
# -----------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CommandHandler("list", list_all))
    app.add_handler(CommandHandler("nigeria", nigeria))
    app.add_handler(CommandHandler("tech", tech))
    app.add_handler(CommandHandler("international", international))

    asyncio.create_task(scheduled_post(app))

    logger.info("BOT RUNNING...")
    await app.run_polling()

# ENTRY POINT
if __name__ == "__main__":
    asyncio.run(main())
