#!/usr/bin/env python3
# main.py — ScoreLaship Hub AI (Google Sheets powered)
# Requirements: pyTelegramBotAPI, gspread, oauth2client, python-dateutil, pytz, schedule

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

# -----------------------------
# CONFIG
# -----------------------------
TZ = pytz.timezone("Africa/Lagos")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # full JSON content
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # numeric string (optional for testing)
# You gave this Spreadsheet ID — embedded here. If you prefer env var, set SPREADSHEET_ID env.
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "18Ms7WOWiu0iKjTl_UCmncViL3j8Q1WR0da06VM8yulM")
SHEET_NAME = os.getenv("SHEET_NAME", None)  # optional sheet name; default first sheet

# Quick validations
print("[STARTUP] BOT_TOKEN present:", bool(BOT_TOKEN))
print("[STARTUP] GOOGLE_SERVICE_ACCOUNT_JSON present:", bool(SA_JSON))
print("[STARTUP] SPREADSHEET_ID:", SPREADSHEET_ID)
print("[STARTUP] GROUP_CHAT_ID present:", bool(GROUP_CHAT_ID))

if not BOT_TOKEN:
    raise EnvironmentError("BOT_TOKEN missing from environment.")
if not SA_JSON:
    raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_JSON missing from environment.")
if not SPREADSHEET_ID:
    raise EnvironmentError("SPREADSHEET_ID missing (set env SPREADSHEET_ID or embed in code).")

bot = telebot.TeleBot(BOT_TOKEN)

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
    sheet = sh.sheet1
    return sheet

try:
    sheet = init_sheet()
    print("[OK] Google Sheet opened.")
except Exception as e:
    print("[ERROR] Could not open sheet:", e)
    traceback.print_exc()
    sheet = None

# -----------------------------
# Footer & settings
# -----------------------------
FOOTER = "\n\n🌐Share to your friends\n\nJoin our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"
POST_TIME_LOCAL = "08:30"  # Lagos local time (HH:MM)

# Exact expected headers (capitalization matters)
REQUIRED_HEADERS = ["Category", "Title", "Benefit", "Criteria", "Requirement", "Deadline", "Link", "Posted"]

# -----------------------------
# Helpers
# -----------------------------
def truthy(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().upper()
    return s in ("TRUE", "T", "1", "YES")

def ensure_headers():
    """Ensure the sheet has the exact header row; add missing headers at end if needed."""
    if not sheet:
        return []
    headers = sheet.row_values(1)
    headers = [h.strip() for h in headers]
    changed = False
    for h in REQUIRED_HEADERS:
        if h not in headers:
            headers.append(h)
            changed = True
    if changed:
        # overwrite header row
        sheet.delete_row(1)
        sheet.insert_row(headers, 1)
        print("[SHEET] Header row updated to include required headers.")
    else:
        print("[SHEET] Headers OK:", headers)
    return headers

def parse_deadline(val):
    if val is None or str(val).strip() == "":
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    try:
        d = dateparser.parse(s, dayfirst=False).date()
        return d
    except Exception:
        return None

def get_all_records():
    if not sheet:
        return []
    return sheet.get_all_records()

# -----------------------------
# Cleanup expired rows
# -----------------------------
def cleanup_expired():
    """Mark rows with Deadline < today as Posted = TRUE (so they never post)."""
    if not sheet:
        return
    headers = sheet.row_values(1)
    if "Posted" not in headers or "Deadline" not in headers:
        print("[CLEANUP] Required columns missing.")
        return
    posted_col = headers.index("Posted") + 1
    deadline_col = headers.index("Deadline") + 1

    rows = sheet.get_all_records()
    today = datetime.now(TZ).date()
    for i, row in enumerate(rows, start=2):
        dl_raw = row.get("Deadline", "")
        dl = parse_deadline(dl_raw)
        if dl and dl < today:
            if not truthy(row.get("Posted")):
                try:
                    sheet.update_cell(i, posted_col, "TRUE")
                    print(f"[CLEANUP] Row {i} expired (deadline {dl_raw}) — marked Posted=TRUE")
                except Exception as e:
                    print("[CLEANUP] Failed to mark expired row", i, e)

# -----------------------------
# Find next unposted item for a category
# -----------------------------
def find_next_unposted(category):
    if not sheet:
        return None, None
    headers = sheet.row_values(1)
    rows = sheet.get_all_records()
    for i, row in enumerate(rows, start=2):
        cat = str(row.get("Category", "")).strip().lower()
        if cat == category.lower() and not truthy(row.get("Posted")):
            return i, row
    return None, None

# -----------------------------
# Post formatting & sending
# -----------------------------
def format_message(row):
    title = row.get("Title", "No title")
    benefit = row.get("Benefit", "")
    criteria = row.get("Criteria", "")
    requirement = row.get("Requirement", "")
    deadline = row.get("Deadline", "")
    link = row.get("Link", "")

    parts = [f"🎓 *{title}*"]
    if benefit:
        parts.append(f"📌 *Benefit:* {benefit}")
    if criteria:
        parts.append(f"📌 *Criteria:* {criteria}")
    if requirement:
        parts.append(f"📌 *Requirement:* {requirement}")
    if deadline:
        parts.append(f"⏳ *Deadline:* {deadline}")
    if link:
        parts.append(f"\n🔗 Apply: {link}")

    msg = "\n".join(parts) + FOOTER
    return msg

def mark_posted(row_index):
    if not sheet:
        return
    headers = sheet.row_values(1)
    try:
        posted_col = headers.index("Posted") + 1
    except ValueError:
        return
    try:
        sheet.update_cell(row_index, posted_col, "TRUE")
        # write DatePosted column if exists or append DatePosted column
        if "DatePosted" in headers:
            dp_col = headers.index("DatePosted") + 1
            sheet.update_cell(row_index, dp_col, datetime.now(TZ).date().isoformat())
    except Exception as e:
        print("[ERROR] mark_posted failed:", e)

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
    """Post next available item — sends to the chat where the command was called."""
    chat_id = m.chat.id
    bot.send_message(chat_id, "⏳ Sending next available scholarship to this chat now...")
    # Try categories in order: nigeria, tech, international
    if post_next_for_category_to_chat("nigeria", chat_id):
        pass
    elif post_next_for_category_to_chat("tech", chat_id):
        pass
    elif post_next_for_category_to_chat("international", chat_id):
        pass
    else:
        bot.send_message(chat_id, "⚠️ No unposted items found in these categories.")
    bot.send_message(chat_id, "✅ Done (attempted posting).")

@bot.message_handler(commands=["testall"])
def cmd_testall(m):
    """Post all unposted (careful) — for testing only."""
    chat_id = m.chat.id
    bot.send_message(chat_id, "⏳ Sending all unposted opportunities now...")
    records = get_all_records()
    posted_any = False
    for idx, row in enumerate(records, start=2):
        if not truthy(row.get("Posted")):
            msg = format_message(row)
            try:
                bot.send_message(chat_id, msg, parse_mode="Markdown")
                sheet.update_cell(idx, sheet.row_values(1).index("Posted") + 1, "TRUE")
                posted_any = True
            except Exception as e:
                print("[ERROR] testall send failed:", e)
    bot.send_message(chat_id, "✅ Done. Posted any unposted items." if posted_any else "⚠️ No unposted items to post.")

# -----------------------------
# Scheduler loop (checks local Lagos time)
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
                    # post one per category
                    post_next_for_category_to_chat("nigeria", gid)
                    post_next_for_category_to_chat("tech", gid)
                    post_next_for_category_to_chat("international", gid)
                except Exception as e:
                    print("[SCHED] GROUP_CHAT_ID invalid or send failed:", e)
            else:
                print("[SCHED] GROUP_CHAT_ID not set — scheduled job skipped.")
            # avoid double-run in same minute
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
bot.infinity_polling()
