so, what happen that the bot is not respodning after testig it? #!/usr/bin/env python3
# main.py — ScoreLaship Hub AI (Robust Version)

import os
import json
import time
import threading
import traceback
from datetime import datetime, date
import pytz
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dateutil import parser as dateparser
from difflib import SequenceMatcher
import re

# -----------------------------
# CONFIG
# -----------------------------
TZ = pytz.timezone("Africa/Lagos")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # full JSON content
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # numeric string (optional)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "18Ms7WOWiu0iKjTl_UCmncViL3j8Q1WR0da06VM8yulM")
SHEET_NAME = os.getenv("SHEET_NAME", None)  # optional sheet name

bot = telebot.TeleBot(BOT_TOKEN)

FOOTER = "\n\n🌐Share to your friends\n\nJoin our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"
POST_TIME_LOCAL = "08:30"

# -----------------------------
# HELPERS
# -----------------------------
def truthy(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().upper()
    return s in ("TRUE", "T", "1", "YES")

def escape_markdown(text):
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def similar(a, b):
    return SequenceMatcher(None, str(a).strip().lower(), str(b).strip().lower()).ratio()

def parse_deadline(val):
    if val is None or str(val).strip() == "":
        return None
    if isinstance(val, date):
        return val
    try:
        s = str(val).strip()
        return dateparser.parse(s, dayfirst=False).date()
    except:
        return None

def get_headers_map(sheet):
    """Return dict mapping lowercase header names → column index (1-based)"""
    headers = sheet.row_values(1)
    return {h.strip().lower(): idx+1 for idx, h in enumerate(headers)}

# -----------------------------
# Google Sheets init
# -----------------------------
def init_sheet():
    try:
        svc_info = json.loads(SA_JSON)
    except Exception as e:
        print("[ERROR] Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON:", e)
        raise
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(svc_info, scope)
    client = gspread.authorize(creds)
    if SHEET_NAME:
        sh = client.open(SHEET_NAME)
    else:
        sh = client.open_by_key(SPREADSHEET_ID)
    return sh.sheet1

try:
    sheet = init_sheet()
    print("[OK] Google Sheet opened.")
except Exception as e:
    print("[ERROR] Could not open sheet:", e)
    traceback.print_exc()
    sheet = None

# -----------------------------
# Sheet utilities
# -----------------------------
def ensure_headers():
    if not sheet:
        return {}
    headers_map = get_headers_map(sheet)
    required_headers = ["category","title","benefit","criteria","requirement","deadline","link","posted"]
    changed = False
    for h in required_headers:
        if h not in headers_map:
            # append missing header
            sheet.update_cell(1, len(headers_map)+1, h.capitalize())
            changed = True
            headers_map = get_headers_map(sheet)
    if changed:
        print("[SHEET] Added missing headers.")
    return headers_map

def get_all_records():
    if not sheet:
        return []
    return sheet.get_all_records()

def cleanup_expired():
    if not sheet:
        return
    headers_map = get_headers_map(sheet)
    if "posted" not in headers_map or "deadline" not in headers_map:
        print("[CLEANUP] Required columns missing.")
        return
    rows = sheet.get_all_records()
    today = datetime.now(TZ).date()
    for i, row in enumerate(rows, start=2):
        dl_raw = row.get("Deadline", "")
        dl = parse_deadline(dl_raw)
        if dl and dl < today:
            if not truthy(row.get("Posted")):
                try:
                    sheet.update_cell(i, headers_map["posted"], "TRUE")
                    print(f"[CLEANUP] Row {i} expired (deadline {dl_raw}) — marked Posted=TRUE")
                except Exception as e:
                    print("[CLEANUP] Failed to mark expired row", i, e)

# -----------------------------
# Posting logic
# -----------------------------
def find_next_unposted(category):
    if not sheet:
        return None, None
    headers_map = get_headers_map(sheet)
    rows = sheet.get_all_records()
    for i, row in enumerate(rows, start=2):
        cat = str(row.get("Category", "")).strip()
        if similar(cat, category) > 0.8 and not truthy(row.get("Posted")):
            return i, row
    return None, None

def format_message(row):
    title = escape_markdown(row.get("Title", "No title"))
    benefit = escape_markdown(row.get("Benefit", ""))
    criteria = escape_markdown(row.get("Criteria", ""))
    requirement = escape_markdown(row.get("Requirement", ""))
    deadline = row.get("Deadline", "")
    link = row.get("Link", "")

    parts = [f"🎓 *{title}*"]
    if benefit: parts.append(f"📌 *Benefit:* {benefit}")
    if criteria: parts.append(f"📌 *Criteria:* {criteria}")
    if requirement: parts.append(f"📌 *Requirement:* {requirement}")
    if deadline: parts.append(f"⏳ *Deadline:* {deadline}")
    if link: parts.append(f"\n🔗 Apply: {link}")

    return "\n".join(parts) + FOOTER

def mark_posted(row_index):
    if not sheet:
        return
    headers_map = get_headers_map(sheet)
    posted_col = headers_map.get("posted")
    if posted_col:
        sheet.update_cell(row_index, posted_col, "TRUE")
        if "dateposted" in headers_map:
            dp_col = headers_map["dateposted"]
            sheet.update_cell(row_index, dp_col, datetime.now(TZ).date().isoformat())

def post_next_for_category_to_chat(category, chat_id):
    cleanup_expired()
    row_idx, row = find_next_unposted(category)
    if not row:
        try:
            bot.send_message(chat_id, f"⚠️ No more *{category.title()}* opportunities available.", parse_mode="Markdown")
        except Exception as e:
            print("[ERROR] failed to send 'no more' message:", e)
        return False

    msg = format_message(row)
    try:
        bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=False)
        mark_posted(row_idx)
        print(f"[POST] Posted row {row_idx} for category {category} to chat {chat_id}")
        return True
    except Exception as e:
        print("[ERROR] send failed:", e)
        traceback.print_exc()
        return False

# -----------------------------
# Bot commands
# -----------------------------
@bot.message_handler(commands=["start"])
def cmd_start(m):
    bot.send_message(m.chat.id, "🤖 ScoreLaship Hub AI active. Use /testpost to post the next available opportunity to this chat. Use /getid to get this chat ID.")

@bot.message_handler(commands=["getid"])
def cmd_getid(m):
    bot.send_message(m.chat.id, f"Chat ID: `{m.chat.id}`\nType: `{m.chat.type}`", parse_mode="Markdown")

@bot.message_handler(commands=["testpost"])
def cmd_testpost(m):
    chat_id = m.chat.id
    bot.send_message(chat_id, "⏳ Sending next available scholarship to this chat now...")
    if post_next_for_category_to_chat("nigeria", chat_id):
        return
    elif post_next_for_category_to_chat("tech", chat_id):
        return
    elif post_next_for_category_to_chat("international", chat_id):
        return
    else:
        bot.send_message(chat_id, "⚠️ No unposted items found in these categories.")
    bot.send_message(chat_id, "✅ Done (attempted posting).")

# -----------------------------
# Scheduler
# -----------------------------
def scheduled_job_runner():
    print("[SCHED] Scheduler thread started, watching for", POST_TIME_LOCAL, "Africa/Lagos")
    while True:
        now_local = datetime.now(TZ)
        hhmm = now_local.strftime("%H:%M")
        if hhmm == POST_TIME_LOCAL:
            print("[SCHED] Triggering scheduled post at", now_local.isoformat())
            if GROUP_CHAT_ID:
                try:
                    gid = int(GROUP_CHAT_ID)
                    post_next_for_category_to_chat("nigeria", gid)
                    post_next_for_category_to_chat("tech", gid)
                    post_next_for_category_to_chat("international", gid)
                except Exception as e:
                    print("[SCHED] GROUP_CHAT_ID invalid or send failed:", e)
            time.sleep(61)
        time.sleep(10)

# -----------------------------
# Startup
# -----------------------------
if sheet:
    ensure_headers()
    print("[STARTUP] Sample rows (first 3):", sheet.get_all_records()[:3])
else:
    print("[STARTUP] Sheet not available; commands will fail.")

sched_thread = threading.Thread(target=scheduled_job_runner, daemon=True)
sched_thread.start()

print("🤖 ScoreLaship Hub AI is ACTIVE!")
bot.infinity_polling() what is the major possible errors, since my bot token, group chat id, spreadsheet id, google seervice account, are all correct
