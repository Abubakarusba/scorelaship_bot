#!/usr/bin/env python3
# ScoreLaship Hub AI — auto-detect GROUP_ID version

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
DATA_FILE = os.getenv("DATA_FILE", "data.json")
POST_HOUR = 8   # 24-hour format
POST_MINUTE = 30

FOOTER = "\n\n🌐 Share to your friends\nJoin our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"

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
            json.dump({"opportunities": [], "group_id": None}, f)
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read JSON: %s", e)
        return {"opportunities": [], "group_id": None}

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
    text = opp.get("text", "")
    return f"🎓 {text}{FOOTER}"

# -----------------------------
# COMMAND HANDLERS
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    data = load_data()
    if chat_type in ("group", "supergroup") and not data.get("group_id"):
        data["group_id"] = chat_id
        save_data(data)
        logger.info(f"Detected and saved GROUP_ID: {chat_id}")
        await update.message.reply_text(f"✅ Group detected and saved. GROUP_ID = {chat_id}")
    else:
        await update.message.reply_text("🤖 ScoreLaship Hub AI active. Use /getid to get this chat ID.\nAvailable commands:\n/list\n/nigeria\n/tech\n/international")

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    logger.info(f"/getid called in chat {chat_id} ({chat_type})")
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
        await update.message.reply_text(f"⚠️ No {category.title()} opportunities available.")
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
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        logger.info("Running scheduled post...")
        data = load_data()
        group_id = data.get("group_id")
        if not group_id:
            logger.warning("No group ID detected yet, skipping scheduled post.")
            continue
        for category in ["nigeria", "tech", "international"]:
            opps = filter_category(data, category)
            for opp in opps:
                try:
                    await app.bot.send_message(group_id, format_opportunity(opp))
                    logger.info(f"Posted {category} opportunity to group {group_id}")
                except Exception as e:
                    logger.error("Failed to post scheduled message: %s", e)
        await asyncio.sleep(60)

# -----------------------------
# MAIN
# -----------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CommandHandler("list", list_all))
    app.add_handler(CommandHandler("nigeria", nigeria))
    app.add_handler(CommandHandler("tech", tech))
    app.add_handler(CommandHandler("international", international))

    # Start scheduled posting task
    asyncio.create_task(scheduled_post(app))

    logger.info("BOT RUNNING...")
    await app.run_polling()

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main())
