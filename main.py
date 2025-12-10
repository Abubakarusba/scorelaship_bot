#!/usr/bin/env python3
# ScoreLaship Hub — DM Opportunity Bot

import os
import json
import traceback
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
from dateutil import parser as dateparser
from difflib import SequenceMatcher
import pytz

# ----------------------
# CONFIG
# ----------------------
TZ = pytz.timezone("Africa/Lagos")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # JSON text
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

bot = telebot.TeleBot(BOT_TOKEN)

# ----------------------
# Helpers
# ----------------------
def similar(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def truthy(v):
    s = str(v).strip().lower()
    return s in ("true", "yes", "1")

def parse_deadline(val):
    if not val:
        return None
    try:
        return dateparser.parse(str(val)).date()
    except:
        return None

# ----------------------
# Google Sheet Init
# ----------------------
def init_sheet():
    try:
        svc_info = json.loads(SA_JSON)
    except Exception as e:
        print("[ERROR] Failed parsing JSON:", e)
        return None

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(svc_info, scope)
    client = gspread.authorize(creds)

    try:
        sh = client.open_by_key(SPREADSHEET_ID)
        print("[OK] Sheet opened")
        return sh.sheet1
    except Exception as e:
        print("[ERROR] Could not open sheet:", e)
        traceback.print_exc()
        return None

sheet = init_sheet()

# ----------------------
# Sheet Utilities
# ----------------------
def get_headers_map():
    if not sheet:
        return {}
    headers = sheet.row_values(1)
    return {h.strip().lower(): i+1 for i, h in enumerate(headers)}

def get_all_data():
    """Fetch sheet records safely."""
    if not sheet:
        return []
    try:
        data = sheet.get_all_records()
        return data
    except Exception as e:
        print("[ERROR] get_all_records failed:", e)
        return []

# ----------------------
# Format message
# ----------------------
def format_msg(row):
    title = row.get("Title", "")
    benefit = row.get("Benefit", "")
    criteria = row.get("Criteria", "")
    requirement = row.get("Requirement", "")
    deadline = row.get("Deadline", "")
    link = row.get("Link", "")

    txt = f"🎓 *{title}*\n"
    if benefit:
        txt += f"📌 Benefit: {benefit}\n"
    if criteria:
        txt += f"📌 Criteria: {criteria}\n"
    if requirement:
        txt += f"📌 Requirement: {requirement}\n"
    if deadline:
        txt += f"⏳ Deadline: {deadline}\n"
    if link:
        txt += f"🔗 Apply: {link}\n"

    return txt

# ----------------------
# Bot Commands (DM ONLY)
# ----------------------
@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(
        m.chat.id,
        "🤖 *ScoreLaship DM Bot Active!*\n\n"
        "Use:\n"
        "`/opportunities` — Get ALL opportunities\n"
        "`/nigeria` — Nigerian opportunities\n"
        "`/tech` — Tech opportunities\n"
        "`/international` — International opportunities\n",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["opportunities"])
def all_ops(m):
    data = get_all_data()
    if not data:
        bot.send_message(m.chat.id, "⚠️ No opportunities found in your Google Sheet.")
        return

    bot.send_message(m.chat.id, f"📚 Found {len(data)} opportunities:")

    for row in data:
        msg = format_msg(row)
        bot.send_message(m.chat.id, msg, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=["nigeria", "tech", "international"])
def filtered_ops(m):
    category = m.text.replace("/", "").strip().lower()
    data = get_all_data()

    if not data:
        bot.send_message(m.chat.id, "⚠️ No opportunities found in your Google Sheet.")
        return

    matches = [r for r in data if similar(r.get("Category", ""), category) > 0.8]

    if not matches:
        bot.send_message(
            m.chat.id,
            f"⚠️ No opportunities available for *{category.title()}*.",
            parse_mode="Markdown"
        )
        return

    bot.send_message(m.chat.id, f"📌 Found {len(matches)} {category.title()} opportunities:")

    for row in matches:
        msg = format_msg(row)
        bot.send_message(m.chat.id, msg, parse_mode="Markdown", disable_web_page_preview=True)

# ----------------------
# Run bot
# ----------------------
print("🤖 ScoreLaship DM Bot ACTIVE!")
bot.infinity_polling()
