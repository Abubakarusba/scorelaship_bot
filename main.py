import os
import requests
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

bot = telebot.TeleBot(BOT_TOKEN)

# --------------------------------------------
# 1. TRUSTED SCHOLARSHIP SOURCES
# --------------------------------------------
SOURCES = [
    "https://www.scholarshipregion.com/aims-scholarship-program/",
    "https://jobs.smartyacad.com/",
    "https://www.ngscholars.net/",
    "https://www.opportunitiesforafricans.com/",
    "https://www.afterschoolafrica.com/",
    "https://www.scholarshipair.com/",
    "https://www.myschoolgist.com/ng/category/scholarships/",
    "https://www.youthopportunities.com/tag/scholarships",
    "https://opportunitiescorners.com/category/scholarships/",
    "https://www.studentshubng.com/scholarships",
    "https://nigerianscholars.com/scholarships/",
    "https://www.fundsforngos.org/category/scholarships/",
    "https://www.studyportals.com/scholarships/",
    "https://www.chevening.org/scholarships/",
    "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
    "https://www.fulbrightprogram.org/",
    "https://www.alliance4africa.org/category/scholarship-opportunities/",
    "https://www.topuniversities.com/student-info/scholarships",
    "https://www.opportunitiescircle.com/category/scholarships/"
]

# --------------------------------------------
# 2. MANUAL SCHOLARSHIP LISTS (EDIT THESE)
# --------------------------------------------

NIGERIAN_SCHOLARSHIPS = [
    # EXAMPLE
    # {
    #   "title": "NNPC Undergraduate Scholarship",
    #   "requirements": "...",
    #   "benefits": "...",
    #   "criteria": "...",
    #   "deadline": "2025-12-30",
    #   "link": "https://example.com"
    # }
]

FREE_TECH_SCHOLARSHIPS = [
    # Add Free Tech Opportunities Here
]

INTERNATIONAL_SCHOLARSHIPS = [
    # Add International Scholarships Here
]

# Track posted scholarships
POSTED = set()

# --------------------------------------------
# 3. HELPERS
# --------------------------------------------

def parse_deadline(date_text):
    try:
        date = datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
        if date <= datetime.date.today():
            return None  # skip expired
        return date
    except:
        return None

def format_message(item):
    return (
        f"📌 *{item['title']}*\n\n"
        f"📍 *Requirements:* {item['requirements']}\n\n"
        f"🎁 *Benefits:* {item['benefits']}\n\n"
        f"📝 *Criteria:* {item['criteria']}\n\n"
        f"⏰ *Deadline:* {item['deadline']}\n\n"
        f"🔗 Apply Here: {item['link']}\n\n"
        "──────────────\n"
        "Shared by *ScoreLaship Hub* — empowering students with opportunities.\n"
    )

# --------------------------------------------
# 4. SCRAPER (LIGHTWEIGHT GENERIC)
# --------------------------------------------

def scrape_source(url):
    try:
        print(f"Scraping: {url}")
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        items = []

        # Generic find-like structure
        posts = soup.find_all(["article", "div"], class_=lambda x: x and "post" in x.lower())

        for p in posts[:5]:
            title_tag = p.find(["h2", "h3"])
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link = title_tag.find("a")["href"] if title_tag.find("a") else url

            text = p.get_text(separator=" ").lower()

            # Rough extraction
            requirements = "Available on website"
            benefits = "Available on website"
            criteria = "See full details on the website"

            # Try to detect dates
            deadline = None
            for word in text.split():
                if "-" in word and len(word) == 10:
                    if parse_deadline(word):
                        deadline = word

            if not deadline:
                continue

            items.append({
                "title": title,
                "requirements": requirements,
                "benefits": benefits,
                "criteria": criteria,
                "deadline": deadline,
                "link": link
            })

        return items

    except Exception as e:
        print("Scraper Error:", e)
        return []

# --------------------------------------------
# 5. PICK NEXT OPPORTUNITY
# --------------------------------------------

def get_next_scholarship(category_list):
    for item in category_list:
        if item["title"] not in POSTED:
            deadline = parse_deadline(item["deadline"])
            if deadline:
                POSTED.add(item["title"])
                return item
    return None

# --------------------------------------------
# 6. MAIN POSTING FUNCTION
# --------------------------------------------

def post_opportunity():
    categories = [
        ("Nigerian Scholarship", NIGERIAN_SCHOLARSHIPS),
        ("Free Tech Opportunity", FREE_TECH_SCHOLARSHIPS),
        ("International Scholarship", INTERNATIONAL_SCHOLARSHIPS)
    ]

    for cat_name, cat_list in categories:
        item = get_next_scholarship(cat_list)
        if item:
            bot.send_message(chat_id=CHAT_ID, text=format_message(item), parse_mode="Markdown")
            return

    # If all empty → scrape
    for link in SOURCES:
        scraped = scrape_source(link)
        for item in scraped:
            if item["title"] not in POSTED:
                POSTED.add(item["title"])
                bot.send_message(chat_id=CHAT_ID, text=format_message(item), parse_mode="Markdown")
                return

# --------------------------------------------
# 7. SCHEDULER
# --------------------------------------------

def start_scheduler():
    timezone = pytz.timezone("Africa/Lagos")
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(post_opportunity, "cron", hour=9, minute=0)  # posts at 9:00 AM
    scheduler.start()
    print("Scheduler started for Africa/Lagos timezone")

# --------------------------------------------
# 8. BOT START
# --------------------------------------------

if __name__ == "__main__":
    print("Bot running...")
    start_scheduler()
    bot.infinity_polling()
