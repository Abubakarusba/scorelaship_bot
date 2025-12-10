import os
import logging
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ParseMode

# ===========================
#  DEBUG MODE ENABLED
# ===========================
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s → %(message)s',
    level=logging.DEBUG
)

# ===========================
# GOOGLE SHEET SETUP
# ===========================
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
CLIENT = gspread.authorize(CREDS)

SHEET = CLIENT.open("ScholarshipDB").sheet1

# ===========================
#  SETTINGS
# ===========================
KEYWORDS = ["nigeria", "tech", "international"]
SPAM_WORDS = ["win", "loan", "bet", "credit", "sugar mummy", "investment"]

GROUP_ID = -100123456789  # <<< Replace with your group ID

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ===========================
#  CLEAN DATA FUNCTION
# ===========================
def get_clean_data():
    try:
        rows = SHEET.get_all_values()

        clean = []
        for row in rows[1:]:  # Skip header
            row = row[1:]     # IGNORE column 1 (timestamp)
            if len(row) < 4:
                continue
            clean.append(row)

        return clean
    except Exception as e:
        logging.error(f"Error reading sheet: {e}")
        return []

# ===========================
#  DAILY AUTO POST
# ===========================
def daily_post(context):
    data = get_clean_data()
    if not data:
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d")

    for item in data:
        title = item[0]
        link = item[1]
        deadline = item[2]
        category = item[3]

        text = f"📌 *{title}*\n🔗 {link}\n⏳ Deadline: {deadline}\n🏷 Category: {category}"

        try:
            context.bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Daily post error: {e}")

# ===========================
#  TEST POST
# ===========================
def testpost(update, context):
    update.message.reply_text("✔ Bot is working!")

# ===========================
#  SPAM FILTER
# ===========================
def handle_messages(update, context):
    msg = update.message.text.lower()

    # SPAM DELETION
    if any(word in msg for word in SPAM_WORDS):
        try:
            context.bot.delete_message(
                chat_id=update.message.chat.id,
                message_id=update.message.message_id
            )
            return
        except:
            pass

    # KEYWORD RESPONSE
    if any(keyword in msg for keyword in KEYWORDS):
        update.message.reply_text(
            "Here is a matching opportunity…\n\nUse /testpost to confirm I am active."
        )

# ===========================
#  MAIN BOT
# ===========================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("testpost", testpost))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_messages))

    # Daily job runs at 9:00 AM every day
    updater.job_queue.run_daily(daily_post, time=datetime.time(hour=9, minute=0))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
