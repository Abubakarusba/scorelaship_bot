import telebot
import schedule
import time
import pytz
import threading
import os

# ========================
# Load Environment Variables
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # Optional for testing; must be numeric if set

if not BOT_TOKEN:
    raise EnvironmentError("BOT_TOKEN missing from environment!")

bot = telebot.TeleBot(BOT_TOKEN)

# ========================
# Footer
# ========================
FOOTER = """
🌐 *Share to your friends*

Join our community 👉 [Click Here](https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt)
"""

# ========================
# Rotating Lists
# ========================
nigeria_list = [
    "🇳🇬 Nigerian Scholarship 1\nDetails..." + FOOTER,
    "🇳🇬 Nigerian Scholarship 2\nDetails..." + FOOTER,
]

international_list = [
    "🌍 International Scholarship 1\nDetails..." + FOOTER,
    "🌍 International Scholarship 2\nDetails..." + FOOTER,
]

tech_list = [
    "💻 Tech Opportunity 1\nDetails..." + FOOTER,
    "💻 Tech Opportunity 2\nDetails..." + FOOTER,
]

# ========================
# Functions to send messages
# ========================
def pop_and_send(lst, chat_id):
    if not lst:
        return
    message = lst.pop(0)
    bot.send_message(chat_id, message, parse_mode="Markdown")

def nigeria_scholarship(chat_id): pop_and_send(nigeria_list, chat_id)
def international_scholarship(chat_id): pop_and_send(international_list, chat_id)
def tech_opportunity(chat_id): pop_and_send(tech_list, chat_id)

# ========================
# Bot Commands
# ========================
@bot.message_handler(commands=['getid'])
def get_group_id(message):
    """Return the chat ID and chat type."""
    chat_id = message.chat.id
    chat_type = message.chat.type  # 'private', 'group', 'supergroup'
    print(f"[LOG] /getid used. Chat ID: {chat_id}, Type: {chat_type}")
    bot.send_message(chat_id, f"Chat ID: {chat_id}\nChat Type: {chat_type}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to ScoreLaship Hub AI!\n"
        "I post:\n"
        "🇳🇬 Nigerian Scholarships — 10:40 AM\n"
        "💻 Tech Opportunities — 1:30 PM\n"
        "🌍 International Scholarships — 7:40 PM"
    )

@bot.message_handler(commands=['nigeria'])
def manual_nigeria(message):
    nigeria_scholarship(message.chat.id)

@bot.message_handler(commands=['international'])
def manual_international(message):
    international_scholarship(message.chat.id)

@bot.message_handler(commands=['tech'])
def manual_tech(message):
    tech_opportunity(message.chat.id)

@bot.message_handler(commands=['testall'])
def manual_test_all(message):
    nigeria_scholarship(message.chat.id)
    tech_opportunity(message.chat.id)
    international_scholarship(message.chat.id)
    bot.send_message(message.chat.id, "✅ All lists sent!")

# ========================
# Scheduler (Africa/Lagos)
# ========================
tz = pytz.timezone("Africa/Lagos")

def scheduled_messages():
    target_id = int(GROUP_CHAT_ID) if GROUP_CHAT_ID else None
    if target_id:
        nigeria_scholarship(target_id)
        tech_opportunity(target_id)
        international_scholarship(target_id)

schedule.every().day.at("10:40").do(lambda: nigeria_scholarship(int(GROUP_CHAT_ID)))
schedule.every().day.at("13:30").do(lambda: tech_opportunity(int(GROUP_CHAT_ID)))
schedule.every().day.at("19:40").do(lambda: international_scholarship(int(GROUP_CHAT_ID)))

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

# ========================
# Debug all messages
# ========================
@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    print(f"[DEBUG] Received: {message.text} | Chat ID: {message.chat.id} | Type: {message.chat.type}")

# ========================
# Start bot
# ========================
print("🤖 ScoreLaship Hub AI is ACTIVE!")
bot.infinity_polling()
