import telebot
import schedule
import time
import pytz
import threading
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============================
# BOT CONFIGURATION
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = 6444120693   # Replace with your group ID

bot = telebot.TeleBot(BOT_TOKEN)

# ============================
# GOOGLE SHEET SETUP
# ============================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("ScoreLashipHub_Scholarships").sheet1  # Your sheet name


# ============================
# FOOTER MESSAGE
# ============================
FOOTER = """
🌐 *Share to your friends*

Join our community 👉 [Click Here](https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt)
"""


# ============================
# FETCH NEXT UNSENT SCHOLARSHIP
# ============================
def get_next_post(category):
    data = sheet.get_all_records()

    for row in data:
        if row["category"] == category and row["sent"] == "no":
            return row

    return None


def mark_as_sent(row_id):
    sheet.update_cell(row_id + 2, 5, "yes")  # Column 5 = "sent"


# ============================
# SEND SCHOLARSHIP
# ============================
def send_scholarship(category):
    row = get_next_post(category)
    if not row:
        print(f"No new posts for {category}")
        return

    message = f"""*{row['title']}*

{row['details']}

[Apply Here]({row['link']})

{FOOTER}
"""
    bot.send_message(CHAT_ID, message, parse_mode="Markdown")

    mark_as_sent(row["id"])  # Mark as sent
    print(f"Sent: {row['title']}")


# ============================
# MANUAL BOT COMMANDS
# ============================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔥 ScoreLaship Hub AI is live and posting automatically!")


@bot.message_handler(commands=['nigeria'])
def send_ng(message):
    send_scholarship("nigeria")


@bot.message_handler(commands=['international'])
def send_inter(message):
    send_scholarship("international")


@bot.message_handler(commands=['tech'])
def send_tech(message):
    send_scholarship("tech")


# ============================
# AUTOMATIC SCHEDULE
# ============================
tz = pytz.timezone("Africa/Lagos")

schedule.every().day.at("10:40").do(lambda: send_scholarship("nigeria"))
schedule.every().day.at("13:30").do(lambda: send_scholarship("tech"))
schedule.every().day.at("19:40").do(lambda: send_scholarship("international"))


def scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)


threading.Thread(target=scheduler, daemon=True).start()

# ============================
# START BOT
# ============================
print("🤖 ScoreLaship Hub AI is running...")
bot.infinity_polling()
