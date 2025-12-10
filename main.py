#!/usr/bin/env python3
# debug_main.py — ScoreLaship Hub AI (Debug / Hardened)

import os
import json
import time
import threading
import traceback
from datetime import datetime, date
import pytz
import re
from difflib import SequenceMatcher

# external libs
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dateutil import parser as dateparser

# -----------------------------
# CONFIG / ENV (load first)
# -----------------------------
# EXACT environment variable NAMES required:
# - BOT_TOKEN
# - GOOGLE_SERVICE_ACCOUNT_JSON
# - GROUP_CHAT_ID (optional)
# - SPREADSHEET_ID (optional; fallback provided)
# - SHEET_NAME (optional)
TZ = pytz.timezone("Africa/Lagos")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "18Ms7WOWiu0iKjTl_UCmncViL3j8Q1WR0da06VM8yulM")
SHEET_NAME = os.getenv("SHEET_NAME", None)
POST_TIME_LOCAL = os.getenv("POST_TIME_LOCAL", "08:30")
FOOTER = "\n\n🌐Share to your friends\n\nJoin our community."

# required headers (lowercase keys)
REQUIRED_HEADERS = ["category", "title", "benefit", "criteria", "requirement", "deadline", "link", "posted"]
OPTIONAL_HEADERS = ["dateposted"]

# header names that indicate a timestamp column to ignore
TIMESTAMP_HEADER_KEYWORDS = [
    "timestamp", "time", "created at", "created", "date created", "submitted at", "submitted"
]

# -----------------------------
# TELEGRAM BOT INIT
# -----------------------------
if not BOT_TOKEN:
    print("[FATAL] BOT_TOKEN environment variable is not set. Exiting.")
    raise SystemExit("BOT_TOKEN is required")

bot = telebot.TeleBot(BOT_TOKEN)
try:
    info = bot.get_me()
    print(f"[DEBUG] Connected to Telegram as @{info.username} (id={info.id})")
except Exception as e:
    print("[ERROR] Could not validate bot token with get_me():", e)
    # don't exit — allow running for debug, but many commands will fail
    traceback.print_exc()

# -----------------------------
# HELPERS
# -----------------------------
def truthy(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().upper()
    return s in ("TRUE", "T", "1", "YES", "Y")

_escape_re = re.compile(r'([_\*\[\]\(\)~`>#+\-=|{}\.!])')
def escape_markdown(text):
    if not text:
        return ""
    return _escape_re.sub(r"\\\1", str(text))

def similar(a, b):
    return SequenceMatcher(None, str(a).strip().lower(), str(b).strip().lower()).ratio()

def parse_deadline(val):
    """Return a date object or None. Accepts date strings, datetimes, or Excel-like strings."""
    if val is None or str(val).strip() == "":
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    try:
        s = str(val).strip()
        # handle cases where a timestamp exists (we expect Option B to remove timestamp column,
        # but some deadline cells might still have datetimes)
        dt = dateparser.parse(s, dayfirst=False)
        return dt.date()
    except Exception:
        return None

# -----------------------------
# Google Sheets utilities (robust)
# -----------------------------
def init_sheet():
    """Return (sheet_obj, raw_sheet) or raise Exception.
    raw_sheet is gspread.Spreadsheet, sheet_obj is Worksheet (sheet1)"""
    if not SA_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")
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
    # prefer first worksheet
    ws = sh.sheet1
    print(f"[DEBUG] Opened spreadsheet: {sh.title} (id={sh.id}), using worksheet: {ws.title}")
    return ws

def _is_timestamp_header(h):
    if not h:
        return False
    s = str(h).strip().lower()
    for kw in TIMESTAMP_HEADER_KEYWORDS:
        if kw in s:
            return True
    return False

def read_sheet_rows_robust(sheet):
    """
    Read sheet values, drop a timestamp column if detected (Option B),
    return (headers_map, rows_list)
    headers_map: dict {lower_header: column_index(1-based after removal)}
    rows_list: list of dicts mapping header -> cell value
    """
    try:
        values = sheet.get_all_values()
    except Exception as e:
        print("[ERROR] sheet.get_all_values() failed:", e)
        raise

    if not values or len(values) == 0:
        print("[DEBUG] Sheet empty (no values).")
        return {}, []

    raw_headers = values[0]
    # detect timestamp column (commonly first column)
    ts_index = None
    for idx, h in enumerate(raw_headers):
        if _is_timestamp_header(h):
            ts_index = idx
            print(f"[DEBUG] Detected timestamp column at index {idx} header='{h}' -> will ignore this column")
            break

    # Build headers excluding timestamp column
    headers = []
    col_map = {}  # lowercase -> col index (1-based) after removal
    out_idx = 0
    for idx, h in enumerate(raw_headers):
        if idx == ts_index:
            continue
        header_clean = str(h).strip()
        if header_clean == "":
            # generate placeholder name (ColumnX)
            header_clean = f"column_{idx+1}"
            print(f"[DEBUG] Empty header detected at raw index {idx}; auto-naming '{header_clean}'")
        out_idx += 1
        headers.append(header_clean)
        col_map[header_clean.strip().lower()] = out_idx  # 1-based

    # Build rows: map header -> value
    rows = []
    for r_idx, row_vals in enumerate(values[1:], start=2):
        # pad row if shorter than headers
        # create a list where timestamp column removed
        cleaned = []
        for idx, v in enumerate(row_vals):
            if idx == ts_index:
                continue
            cleaned.append(v)
        # if row shorter, pad with ""
        while len(cleaned) < len(headers):
            cleaned.append("")
        row_dict = {}
        for h, v in zip(headers, cleaned):
            row_dict[h] = v
        rows.append(row_dict)

    # normalize headers_map to lowercase -> 1-based index
    headers_map = {k.lower(): v for k, v in col_map.items()}
    print(f"[DEBUG] headers_map after removal: {headers_map}")
    return headers_map, rows

# -----------------------------
# Module-level sheet initialization
# -----------------------------
sheet = None
try:
    sheet = init_sheet()
    print("[OK] Google Sheet opened.")
except Exception as e:
    print("[ERROR] Could not open sheet:", e)
    traceback.print_exc()
    sheet = None

# -----------------------------
# Sheet helpers that use robust reader
# -----------------------------
def ensure_headers():
    """Ensure required headers exist; if missing create them in the sheet (appends to header row)."""
    if not sheet:
        print("[ensure_headers] Sheet not available.")
        return {}

    headers_map, rows = read_sheet_rows_robust(sheet)
    # find missing headers (case-insensitive)
    missing = [h for h in REQUIRED_HEADERS if h not in headers_map]
    if missing:
        print(f"[SHEET] Missing headers detected: {missing} — adding to sheet header row.")
        # append to the header row (we'll fetch current header row to place them)
        try:
            raw_headers = sheet.row_values(1)
            # if timestamp column existed, ensure we place new headers at the right columns:
            # compute target column index as current number of header columns +1
            start_col = len(raw_headers) + 1
            for i, h in enumerate(missing):
                col = start_col + i
                sheet.update_cell(1, col, h.capitalize())
                print(f"[SHEET] Added header '{h.capitalize()}' at column {col}")
        except Exception as e:
            print("[ERROR] Failed to add missing headers:", e)
            traceback.print_exc()
        # re-read headers_map
        headers_map, rows = read_sheet_rows_robust(sheet)
    else:
        print("[SHEET] All required headers present.")
    return headers_map

def get_all_records_robust():
    """Return list of row dicts using cleaned headers (timestamp column removed)."""
    if not sheet:
        return []
    _, rows = read_sheet_rows_robust(sheet)
    return rows

def cleanup_expired():
    if not sheet:
        print("[CLEANUP] No sheet available.")
        return
    headers_map, rows = read_sheet_rows_robust(sheet)
    # keys in rows are the original header names (not normalized). We'll do case-insensitive lookups.
    today = datetime.now(TZ).date()
    for idx, row in enumerate(rows, start=2):
        # row is dict header->value (header as original string)
        # case-insensitive get:
        dl_val = None
        # look for a key that lower() == 'deadline'
        for k in row.keys():
            if k.strip().lower() == "deadline":
                dl_val = row.get(k)
                break
        posted_val = None
        for k in row.keys():
            if k.strip().lower() == "posted":
                posted_val = row.get(k)
                posted_key_name = k
                break
        dl = parse_deadline(dl_val)
        if dl and dl < today:
            if not truthy(posted_val):
                try:
                    # update posted column using headers_map
                    posted_col = headers_map.get("posted")
                    if not posted_col:
                        # fallback: find col index by searching header row
                        hdrs = sheet.row_values(1)
                        for i, h in enumerate(hdrs, start=1):
                            if h.strip().lower() == "posted":
                                posted_col = i
                                break
                    if posted_col:
                        sheet.update_cell(idx, posted_col, "TRUE")
                        print(f"[CLEANUP] Row {idx} expired (deadline {dl_val}) — marked Posted=TRUE")
                    else:
                        print("[CLEANUP] Cannot find 'posted' column index to mark row", idx)
                except Exception as e:
                    print("[CLEANUP] Failed to mark expired row", idx, e)

# -----------------------------
# Posting logic (uses robust reader)
# -----------------------------
def find_next_unposted(category):
    if not sheet:
        return None, None
    headers_map, rows = read_sheet_rows_robust(sheet)
    for i, row in enumerate(rows, start=2):
        # find category key case-insensitively
        cat_val = ""
        posted_val = ""
        # map keys
        for k, v in row.items():
            kl = k.strip().lower()
            if kl == "category":
                cat_val = v
            if kl == "posted":
                posted_val = v
        if similar(cat_val, category) > 0.8 and not truthy(posted_val):
            return i, row
    return None, None

def format_message(row):
    # case-insensitive extraction
    def _get(key):
        for k, v in row.items():
            if k.strip().lower() == key:
                return v
        return ""
    title = escape_markdown(_get("title") or "No title")
    benefit = escape_markdown(_get("benefit"))
    criteria = escape_markdown(_get("criteria"))
    requirement = escape_markdown(_get("requirement"))
    deadline = _get("deadline") or ""
    link = _get("link") or ""
    parts = [f"🎓 *{title}*"]
    if benefit: parts.append(f"📌 *Benefit:* {benefit}")
    if criteria: parts.append(f"📌 *Criteria:* {criteria}")
    if requirement: parts.append(f"📌 *Requirement:* {requirement}")
    if deadline: parts.append(f"⏳ *Deadline:* {deadline}")
    if link: parts.append(f"\n🔗 Apply: {link}")
    return "\n".join(parts) + FOOTER

def mark_posted(row_index):
    if not sheet:
        print("[mark_posted] Sheet not available.")
        return
    headers_map, _ = read_sheet_rows_robust(sheet)
    # attempt to find 'posted' col index
    posted_col = headers_map.get("posted")
    if not posted_col:
        # fallback lookup directly from header row
        hdrs = sheet.row_values(1)
        for i, h in enumerate(hdrs, start=1):
            if h.strip().lower() == "posted":
                posted_col = i
                break
    if posted_col:
        try:
            sheet.update_cell(row_index, posted_col, "TRUE")
            # update dateposted if exists
            dp_col = headers_map.get("dateposted")
            if dp_col:
                sheet.update_cell(row_index, dp_col, datetime.now(TZ).date().isoformat())
            print(f"[mark_posted] Marked row {row_index} posted (col {posted_col}).")
        except Exception as e:
            print("[mark_posted] Failed to update posted/dateposted:", e)
            traceback.print_exc()
    else:
        print("[mark_posted] Could not find 'posted' column to update.")

def post_next_for_category_to_chat(category, chat_id):
    print(f"[POST] Looking for next unposted item in category '{category}' to chat {chat_id}")
    try:
        cleanup_expired()
    except Exception as e:
        print("[POST] cleanup_expired() threw:", e)
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
        print(f"[POST] Posted row {row_idx} for category '{category}' to chat {chat_id}")
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
    # try prioritized categories
    if post_next_for_category_to_chat("nigeria", chat_id):
        return
    if post_next_for_category_to_chat("tech", chat_id):
        return
    if post_next_for_category_to_chat("international", chat_id):
        return
    bot.send_message(chat_id, "⚠️ No unposted items found in these categories.")
    bot.send_message(chat_id, "✅ Done (attempted posting).")

# -----------------------------
# Scheduler
# -----------------------------
def scheduled_job_runner():
    print(f"[SCHED] Scheduler thread started, watching for {POST_TIME_LOCAL} ({TZ.zone})")
    while True:
        try:
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
                else:
                    print("[SCHED] GROUP_CHAT_ID not set; skipping scheduled posting.")
                # avoid double-triggering within same minute
                time.sleep(61)
        except Exception as e:
            print("[SCHED] Exception in scheduler loop:", e)
            traceback.print_exc()
        time.sleep(10)

# -----------------------------
# STARTUP
# -----------------------------
if sheet:
    try:
        headers_map = ensure_headers()
        sample_rows = get_all_records_robust()[:3]
        print("[STARTUP] Sample rows (first 3):", sample_rows)
    except Exception as e:
        print("[STARTUP] Error during header ensure/read:", e)
        traceback.print_exc()
else:
    print("[STARTUP] Sheet not available; commands that require sheet will fail.")

sched_thread = threading.Thread(target=scheduled_job_runner, daemon=True)
sched_thread.start()

print("🤖 ScoreLaship Hub AI (debug) is ACTIVE!")
try:
    bot.infinity_polling()
except KeyboardInterrupt:
    print("Shutdown requested by user.")
except Exception as e:
    print("[FATAL] bot.infinity_polling() crashed:", e)
    traceback.print_exc()
