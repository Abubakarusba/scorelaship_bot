import telebot
import schedule
import time
import pytz
import threading
import os

# ========================
# Load Bot Token
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = 6444120693  # Your Telegram group ID

bot = telebot.TeleBot(BOT_TOKEN)

# ========================
# Footer
# ========================
FOOTER = """
🌐 *Share to your friends*

Join our community 👉 [Click Here](https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt)
"""

# =====================================================
# 📌 ROTATING CONTENT LISTS
# =====================================================

# ---------- Nigerian Scholarships ----------
nigeria_list = [
    """🇳🇬 *Nigerian Scholarship Update*\n
*One Youth Young Leaders Scholarship 2025 – Fully Funded*\n
• Scholarship worth ₦1m  
• Tuition + Living Stipends  
• 4.5 CGPA minimum  
*Deadline:* Nov 30, 2025  
[Apply Here](https://docs.google.com/forms/d/1UpUO6-q9bOJ8F6Qdjk00i7iRymK16047x6pui0oJrsM/viewform)
""" + FOOTER,

    """🇳🇬 *Nigerian Scholarship: MTN Foundation Scholarship 2025*\n
• ₦300,000 yearly  
• For STEM students  
• Requires good academic performance  
*Deadline:* December 15, 2025  
[Apply](https://www.mtn.ng/scholarships)
""" + FOOTER,
]

# ---------- International Scholarships ----------
international_list = [
    """🌍 *International Scholarship Update*\n
*Global Future Leaders Scholarship 2025 (Fully Funded)*\n
• Full tuition  
• Monthly stipend  
• Visa & flight support  
*Deadline:* Nov 30, 2025  
[Apply](https://example.com/apply)
""" + FOOTER,

    """🌍 *Japanese Government MEXT Scholarship 2025*\n
• Tuition fully covered  
• Monthly stipend  
• No IELTS required for many universities  
*Deadline:* January 2026  
[Apply](https://www.studyinjapan.go.jp)
""" + FOOTER,
]

# ---------- Tech Opportunities ----------
tech_list = [
    """💻 *Free Tech Opportunity – Verified*\n
*Google Career Certificates (FREE via Scholarships)*\n
• Data Analytics  
• UX Design  
• Cybersecurity  
• IT Support  
*Certificate by Google*  
[Apply Free](https://www.coursera.org/google)
""" + FOOTER,

    """💻 *Microsoft Learn Cybersecurity Skilling Program* (100% Free)\n
• Beginner friendly  
• Cloud Security  
• SOC Analyst  
• Job-ready skills  
[Join Here](https://learn.microsoft.com)
""" + FOOTER,
]

# =====================================================
# 📌 FUNCTIONS TO SEND + ROTATE
# =====================================================

def pop_and_send(lst):
    """Send first item and remove it to prevent repetition."""
    if not lst:
        return
    message = lst.pop(0)
    bot.send_message(CHAT_ID, message, parse_mode="Markdown")

def nigeria_scholarship():
    pop_and_send(nigeria_list)

def international_scholarship():
    pop_and_send(international_list)

def tech_opportunity():
    pop_and_send(tech_list)

# =====================================================
# 📌 Bot Commands
# =====================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,
        "👋 *Welcome to ScoreLaship Hub AI!*\n\n"
        "I post:\n"
        "🇳🇬 Nigerian Scholarships — 10:40 AM\n"
        "💻 Tech Opportunities — 1:30 PM\n"
        "🌍 International Scholarships — 7:40 PM\n\n"
        "Everything is *verified* and *never repeated*."
    )

@bot.message_handler(commands=['nigeria'])
def manual_nigeria(message):
    nigeria_scholarship()

@bot.message_handler(commands=['international'])
def manual_international(message):
    international_scholarship()

@bot.message_handler(commands=['tech'])
def manual_tech(message):
    tech_opportunity()

# =====================================================
# 📌 Scheduler (Africa/Lagos)
# =====================================================
tz = pytz.timezone("Africa/Lagos")

schedule.every().day.at("10:40").do(nigeria_scholarship)
schedule.every().day.at("13:30").do(tech_opportunity)
schedule.every().day.at("19:40").do(international_scholarship)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler).start()

# ========================
# Start bot
# ========================
print("🤖 ScoreLaship Hub AI is ACTIVE!")
bot.infinity_polling()
