import telebot
import schedule
import time
import pytz
import threading
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# =======================================
# Load Environment Variables (Railway Safe)
# =======================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # numeric string
SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # full JSON text

if not BOT_TOKEN:
    raise EnvironmentError("❌ BOT_TOKEN missing in Railway Variables.")

if not SA_JSON:
    raise EnvironmentError("❌ GOOGLE_SERVICE_ACCOUNT_JSON missing in Railway Variables.")

bot = telebot.TeleBot(BOT_TOKEN)

# =======================================
# Google Sheets Setup
# =======================================
service_account_info = json.loads(SA_JSON)

creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

client = gspread.authorize(creds)

# Replace with your actual Sheet ID
SHEET_ID = os.getenv("SHEET_ID")

if not SHEET_ID:
    raise EnvironmentError("❌ SHEET_ID missing in Railway Variables.")

sheet = client.open_by_key(SHEET_ID).sheet1


# =======================================
# FOOTER
# =======================================
FOOTER = """
🌐 *Share to your friends*

Join our community 👉 [Click Here](https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt)
"""


# =======================================
# Fetch NEXT unposted scholarship by type
# =======================================
def get_next_unposted(category):
    """Returns next unposted row for this category."""
    records = sheet.get_all_records()

    for i, row in enumerate(records, start=2):  # row 2 = first data row
        if row["Posted"] == False and row["Category"].lower() == category:
            return i, row

    return None, None


def mark_posted(row_number):
    """Marks given row as posted."""
    sheet.update_cell(row_number, 4, "TRUE")  # Column 4 = Posted


# =======================================
# Main send function
# =======================================
def send_scholarship(category, chat_id):
    row_num, row = get_next_unposted(category)

    if not row:
        bot.send_message(chat_id, f"No more *{category.upper()}* scholarships available.", parse_mode="Markdown")
        return

    message = f"""
*{row['Title']}*
{row['Details']}

{FOOTER}
"""

    bot.send_message(chat_id, message, parse_mode="Markdown")

    mark_posted(row_num)


# =======================================
# Bot Commands
# =======================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "👋 *Welcome to ScoreLaship Hub AI!*\n\n"
        "I automatically send:\n"
        "🇳🇬 Nigerian Scholarships — *10:40 AM*\n"
        "💻 Tech Opportunities — *1:30 PM*\n"
        "🌍 International Scholarships — *7:40 PM*",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['getid'])
def get_chat_id(message):
    bot.send_message(message.chat.id, f"Chat ID: `{message.chat.id}`", parse_mode="Markdown")


@bot.message_handler(commands=['nigeria'])
def manual_nigeria(message):
    send_scholarship("nigeria", message.chat.id)


@bot.message_handler(commands=['tech'])
def manual_tech(message):
    send_scholarship("tech", message.chat.id)


@bot.message_handler(commands=['international'])
def manual_int(message):
    send_scholarship("international", message.chat.id)


@bot.message_handler(commands=['testall'])
def test_all(message):
    chat = message.chat.id
    send_scholarship("nigeria", chat)
    send_scholarship("tech", chat)
    send_scholarship("international", chat)
    bot.send_message(chat, "✅ All categories tested!", parse_mode="Markdown")


# =======================================
# Scheduler (Africa/Lagos)
# =======================================
def run_scheduler():
    schedule.every().day.at("10:40").do(lambda: send_scholarship("nigeria", int(GROUP_CHAT_ID)))
    schedule.every().day.at("13:30").do(lambda: send_scholarship("tech", int(GROUP_CHAT_ID)))
    schedule.every().day.at("19:40").do(lambda: send_scholarship("international", int(GROUP_CHAT_ID)))

    while True:
        schedule.run_pending()
        time.sleep(2)


scheduler = threading.Thread(target=run_scheduler)
scheduler.daemon = True
scheduler.start()


# =======================================
# Debug All Messages
# =======================================
@bot.message_handler(func=lambda message: True)
def log_msg(message):
    print(f"[DEBUG] {message.text} | ID: {message.chat.id}")


# =======================================
# START BOT
# =======================================
print("🤖 ScoreLaship Hub AI is ACTIVE!")
bot.infinity_polling()
