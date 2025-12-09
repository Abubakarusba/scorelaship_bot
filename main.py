#!/usr/bin/env python3
# post_scholarships.py — Immediate posting to Telegram group

import os
import telebot
from datetime import datetime

# -----------------------------
# ENV VARIABLES
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # make sure it’s a number

bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------------
# FOOTER
# -----------------------------
FOOTER = "\n\n🌐Share to your friends\nJoin our community: https://chat.whatsapp.com/LwPfFoi2T2O6oXuRXpoZfd?mode=wwt"

# -----------------------------
# MANUAL SCHOLARSHIP LISTS
# -----------------------------
INTERNATIONAL_SCHOLARSHIPS = [
    {
        "title": "2026 UM Global Studies Scholarship in Netherlands For Undergraduates | Fully Funded",
        "requirements": "Undergraduate students from all countries",
        "benefits": "Full Scholarship with €15,930 stipend per year, Travel Costs & Accommodation",
        "criteria": "Undergraduate Study",
        "deadline": "2026-02-01",
        "link": "https://www.scholarshipregion.com/um-global-studies-scholarship/"
    },
    {
        "title": "University of Idaho Masters Scholarship in USA 2026",
        "requirements": "All Countries eligible for Masters Study",
        "benefits": "",
        "criteria": "Masters Study",
        "deadline": "2025-12-15",
        "link": "https://www.scholarshipregion.com/university-of-idaho-masters-scholarship/"
    },
    {
        "title": "Jim Leech Mastercard Foundation Fellowship For Students & Graduates 2026 | $15,000 Opportunity",
        "requirements": "African Countries eligible",
        "benefits": "$15,000 Fellowship",
        "criteria": "Competitions",
        "deadline": "2025-12-15",
        "link": "https://www.scholarshipregion.com/jim-leech-mastercard-foundation-fellowship/"
    },
    {
        "title": "OECD Young Associate Program 2026 (Paid Opportunity)",
        "requirements": "All Countries eligible",
        "benefits": "Paid Internship/Training",
        "criteria": "Internships | Training",
        "deadline": "2025-12-14",
        "link": "https://www.scholarshipregion.com/oecd-young-associate-program/"
    }
]

# -----------------------------
# POSTING FUNCTION
# -----------------------------
def post_scholarships(chat_id, scholarships):
    today = datetime.now().date()
    for s in scholarships:
        # Skip expired scholarships
        deadline_date = datetime.strptime(s["deadline"], "%Y-%m-%d").date()
        if deadline_date <= today:
            continue
        
        # Build message
        parts = [
            f"🎓 *{s['title']}*",
            f"📌 *Requirements:* {s['requirements']}" if s['requirements'] else "",
            f"📌 *Benefits:* {s['benefits']}" if s['benefits'] else "",
            f"📌 *Criteria:* {s['criteria']}" if s['criteria'] else "",
            f"⏳ *Deadline:* {s['deadline']}" if s['deadline'] else "",
            f"\n🔗 Apply: {s['link']}" if s['link'] else ""
        ]
        message = "\n".join([p for p in parts if p]) + FOOTER
        
        # Send to Telegram
        try:
            bot.send_message(chat_id, message, parse_mode="Markdown", disable_web_page_preview=False)
            print(f"[POSTED] {s['title']}")
        except Exception as e:
            print(f"[ERROR] Failed to post {s['title']}: {e}")

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    post_scholarships(GROUP_CHAT_ID, INTERNATIONAL_SCHOLARSHIPS)
    print("✅ All scholarships posted (or skipped if expired).")
