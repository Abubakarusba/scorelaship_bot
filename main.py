import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import schedule
import time

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Google Service Account JSON
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# Google Sheets Setup
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(SERVICE_JSON), scope)
client = gspread.authorize(creds)

# Open Sheet
SHEET_NAME = "Opportunities"
sheet = client.open(SHEET_NAME).sheet1

# TIMEZONE
TZ = pytz.timezone("Africa/Lagos")

# FOOTER
FOOTER = """\n\n🌐Share to your friends

Join our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"""

def check_deadlines_and_cleanup():
    """Automatically mark outdated opportunities as posted."""
    rows = sheet.get_all_records()

    for idx, row in enumerate(rows, start=2):
        deadline_str = row.get("Deadline", "").strip()
        posted = row.get("Posted", "FALSE")

        if not deadline_str:
            continue

        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
            now = datetime.now(TZ)

            if deadline < now:
                # Mark as TRUE so bot never posts it
                sheet.update_cell(idx, list(row.keys()).index("Posted") + 1, "TRUE")
        except:
            continue

def post_opportunities():
    """Post unposted opportunities to the Telegram channel."""
    check_deadlines_and_cleanup()  # clean expired ones first

    rows = sheet.get_all_records()

    for idx, row in enumerate(rows, start=2):
        if str(row.get("Posted")).upper() == "TRUE":
            continue

        title = row.get("Title", "No Title")
        description = row.get("Description", "No Description")
        deadline = row.get("Deadline", "No Deadline")
        link = row.get("Link", "No Link")

        message = f"🎓 *{title}*\n\n{description}\n\n📅 Deadline: *{deadline}*\n🔗 Apply: {link}{FOOTER}"

        try:
            bot.send_message(os.getenv("CHANNEL_ID"), message, parse_mode="Markdown")
            sheet.update_cell(idx, list(row.keys()).index("Posted") + 1, "TRUE")
        except Exception as e:
            print(f"Error sending message: {e}")

# --------------------------
# /testpost command
# --------------------------
@bot.message_handler(commands=['testpost'])
def handle_testpost(message):
    """Force the bot to post immediately."""
    bot.send_message(message.chat.id, "⏳ Sending next available scholarship now...")
    post_opportunities()
    bot.send_message(message.chat.id, "✅ Done posting available scholarships!")

# --------------------------
# Scheduler
# --------------------------
def run_scheduler():
    schedule.every().day.at("08:30").do(post_opportunities)

    while True:
        schedule.run_pending()
        time.sleep(1)

# --------------------------
# Start Bot
# --------------------------
print("Bot running...")
# Run scheduler in a separate thread
import threading
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

# Start polling
bot.infinity_polling()
