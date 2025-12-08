# main.py - debug-friendly version
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

# -----------------------------
# CONFIG / ENV
# -----------------------------
TZ = pytz.timezone("Africa/Lagos")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # string numeric, e.g. -100123...
SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
SHEET_NAME = os.getenv("SHEET_NAME", "Opportunities")  # default sheet name

# Basic checks
print("[STARTUP] Checking required environment variables...")
print(f"BOT_TOKEN present: {'YES' if BOT_TOKEN else 'NO'}")
print(f"GROUP_CHAT_ID present: {'YES' if GROUP_CHAT_ID else 'NO'}")
print(f"GOOGLE_SERVICE_ACCOUNT_JSON present: {'YES' if SA_JSON else 'NO'}")
print(f"SHEET_NAME: {SHEET_NAME}")

if not BOT_TOKEN:
    raise EnvironmentError("BOT_TOKEN missing")
if not SA_JSON:
    raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_JSON missing")
# GROUP_CHAT_ID is optional for testing; /testpost will send to the chat where command is run.

bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------------
# Google Sheets auth
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
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

try:
    sheet = init_sheet()
    print("[OK] Google Sheet opened:", SHEET_NAME)
except Exception as e:
    print("[ERROR] Could not open sheet:", e)
    traceback.print_exc()
    sheet = None

# -----------------------------
# FOOTER
# -----------------------------
FOOTER = "\n\n🌐Share to your friends\n\nJoin our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"

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
    """Print headers to logs and ensure required headers exist; return header list."""
    if not sheet:
        return []
    headers = sheet.row_values(1)
    print("[SHEET] Headers found:", headers)
    required = ["Category", "Title", "Benefit", "Criteria", "Requirement", "Deadline", "Link", "Posted"]
    # Add missing headers at the end (non-destructive)
    missing = [h for h in required if h not in headers]
    if missing:
        print("[SHEET] Missing headers detected. Adding:", missing)
        # append missing header names
        for h in missing:
            sheet.update_cell(1, len(headers) + 1, h)
            headers.append(h)
    return headers

def sample_rows(n=3):
    if not sheet:
        return []
    rows = sheet.get_all_records()
    return rows[:n]

def parse_date(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    # try loose parse
    try:
        from dateutil import parser
        return parser.parse(s, dayfirst=False).date()
    except Exception:
        return None

# -----------------------------
# Expiration and posting logic
# -----------------------------
def cleanup_expired_and_invalid():
    """Mark as Posted=TRUE any row with Deadline < today or invalid date where needed."""
    if not sheet:
        print("[CLEANUP] No sheet available.")
        return
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    posted_col_index = None
    try:
        posted_col_index = headers.index("Posted") + 1
    except ValueError:
        print("[CLEANUP] Posted column not found.")
        return

    today = datetime.now(TZ).date()
    for i, row in enumerate(rows, start=2):
        dl_raw = row.get("Deadline", "")
        posted = truthy(row.get("Posted"))
        dl_date = parse_date(dl_raw)
        if dl_date and dl_date < today and not posted:
            try:
                sheet.update_cell(i, posted_col_index, "TRUE")
                print(f"[CLEANUP] Row {i} expired (deadline {dl_raw}) -> marked Posted=TRUE")
            except Exception as e:
                print("[CLEANUP] Failed to mark row", i, e)

def find_next_unposted_for_category(category):
    if not sheet:
        return None, None, None
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    posted_col_index = headers.index("Posted") + 1 if "Posted" in headers else None
    for i, row in enumerate(rows, start=2):
        cat = str(row.get("Category","")).strip().lower()
        if cat == category.lower() and not truthy(row.get("Posted")) and not truthy(row.get("Expired", False)):
            return i, row, headers
    return None, None, headers

def mark_row_posted(row_index):
    headers = sheet.row_values(1)
    try:
        posted_col = headers.index("Posted") + 1
        sheet.update_cell(row_index, posted_col, "TRUE")
        # optionally write DatePosted cell if you have a column
    except Exception as e:
        print("[ERROR] mark_row_posted failed:", e)

def format_message_from_row(row):
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
        parts.append(f"\n🔗 Apply here: {link}")
    msg = "\n".join(parts) + FOOTER
    return msg

def post_next_for_category(category, target_chat_id):
    try:
        cleanup_expired_and_invalid()
        row_idx, row, headers = find_next_unposted_for_category(category)
        if not row:
            bot.send_message(target_chat_id, f"⚠️ No more *{category.title()}* opportunities available.", parse_mode="Markdown")
            print(f"[POST] No unposted row found for {category}")
            return False
        msg = format_message_from_row(row)
        bot.send_message(target_chat_id, msg, parse_mode="Markdown", disable_web_page_preview=False)
        mark_row_posted(row_idx)
        print(f"[POST] Posted row {row_idx} for category {category} to chat {target_chat_id}")
        return True
    except Exception as e:
        print("[ERROR] post_next_for_category failed:", e)
        traceback.print_exc()
        return False

# -----------------------------
# Command handlers
# -----------------------------
@bot.message_handler(commands=['start'])
def cmd_start(m):
    bot.send_message(m.chat.id, "Bot active. Use /testpost to post next item to this chat.")

@bot.message_handler(commands=['getid'])
def cmd_getid(m):
    bot.send_message(m.chat.id, f"Chat ID: `{m.chat.id}`\nType: `{m.chat.type}`", parse_mode="Markdown")

@bot.message_handler(commands=['testpost'])
def cmd_testpost(m):
    """Force a post to the chat where command was invoked."""
    chat_id = m.chat.id
    bot.send_message(chat_id, "⏳ Sending next available scholarship to this chat now...")
    # Try to post Nigeria, Tech, International in order; or just pick one
    posted = post_next_for_category("nigeria", chat_id)
    if not posted:
        posted = post_next_for_category("tech", chat_id)
    if not posted:
        posted = post_next_for_category("international", chat_id)
    bot.send_message(chat_id, "✅ Done (attempted posting).")

@bot.message_handler(commands=['debuginfo'])
def cmd_debuginfo(m):
    """Print debug info to logs and reply with short status."""
    headers = ensure_headers()
    sample = sample_rows(3)
    print("[DEBUGINFO] Headers:", headers)
    print("[DEBUGINFO] Sample rows:", sample)
    bot.send_message(m.chat.id, "Debug info printed to server logs.")

# -----------------------------
# Scheduler: run daily posted job (but test via /testpost)
# -----------------------------
def scheduled_job():
    print("[SCHED] Running scheduled_job at", datetime.now(TZ).isoformat())
    # Use GROUP_CHAT_ID env variable if set
    if GROUP_CHAT_ID:
        try:
            gid = int(GROUP_CHAT_ID)
        except Exception:
            print("[SCHED] GROUP_CHAT_ID invalid:", GROUP_CHAT_ID)
            return
        # Post one per category (or adapt)
        post_next_for_category("nigeria", gid)
        post_next_for_category("tech", gid)
        post_next_for_category("international", gid)
    else:
        print("[SCHED] GROUP_CHAT_ID not set; scheduled job skipped.")

def run_scheduler_loop():
    # simple loop every minute checks local time and posts at 08:30
    while True:
        now = datetime.now(TZ)
        hhmm = now.strftime("%H:%M")
        if hhmm == "08:30":
            scheduled_job()
            time.sleep(61)  # avoid double-run within same minute
        time.sleep(10)

# -----------------------------
# Startup actions
# -----------------------------
if sheet:
    ensure_headers()
    print("[STARTUP] Sample rows:", sample_rows(3))
else:
    print("[STARTUP] Sheet not initialized; commands will fail.")

# start scheduler thread
sched_thread = threading.Thread(target=run_scheduler_loop, daemon=True)
sched_thread.start()

print("[BOT] Starting polling...")
bot.infinity_polling()
