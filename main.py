import os
import asyncio
import threading
import requests
import logging
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- [1. LOGGING & SERVER SETUP] ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): return "POS Bot is Live and Ready!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [2. CONFIGURATION - အားလုံး စစ်ပြီးသား Keys များ] ---
TELEGRAM_BOT_TOKEN = "8630792505:AAFHcwkRWZXtAGX87-DBu7pl7j7rYPFul0k"
# Screenshot ထဲကအတိုင်း Hyphen မပါသော Key အမှန်
GEMINI_API_KEY = "AIzaSyD1LSZZ0gxep7ol4fItYDuDtkJddQ_H6tw"
NOTION_TOKEN = "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"
DATABASE_ID = "32f72c14272f80548ac1c464a10d92a2"

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# --- [3. NOTION FUNCTION] ---
def get_notion_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    try:
        res = requests.post(url, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()
        items = []
        for row in data.get("results", []):
            try:
                # Notion Column အမည်များ: 'Product Name' နှင့် 'Selling Price'
                name = row["properties"]["Product Name"]["title"][0]["plain_text"]
                price = row["properties"]["Selling Price"]["number"]
                items.append(f"• {name}: {price} MMK")
            except Exception:
                continue
        
        if items:
            return "🛍️ **လက်ရှိရောင်းရန်ပစ္စည်းများ**\n\n" + "\n".join(items)
        else:
            return "📦 စာရင်းထဲမှာ ပစ္စည်းအမည် သို့မဟုတ် ဈေးနှုန်း သေချာမဖြည့်ရသေးပါဘူး။"
            
    except Exception as e:
        logger.error(f"Notion Error: {e}")
        return "⚠️ Notion ချိတ်ဆက်မှု အခက်အခဲရှိနေပါတယ်။ (Connection စစ်ပေးပါ)"

# --- [4. MESSAGE HANDLER] ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    logger.info(f"📩 စာဝင်လာပါပြီ: {user_text}")

    # Menu Keywords စစ်ခြင်း
    menu_keywords = ["ဘာရလဲ", "menu", "ဈေး", "list", "ပစ္စည်း", "ဈေးနှုန်း", "ရောင်းဖို့"]
    if any(kw in user_text.lower() for kw in menu_keywords):
        reply = get_notion_data()
    else:
        # Gemini AI ကို မေးမြန်းခြင်း
        try:
            prompt = f"You are a helpful Burmese Shop Assistant for a POS system. Answer this concisely: {user_text}"
            response = ai_model.generate_content(prompt)
            reply = response.text if response.text else "⚠️ AI က အဖြေမထုတ်ပေးနိုင်ပါဘူး။"
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            reply = "⚠️ Gemini AI နဲ့ ချိတ်ဆက်လို့မရပါဘူး။ (API Key အခြေအနေ စစ်ပေးပါ)"
    
    await update.message.reply_text(reply)

# --- [5. MAIN START] ---
async def main():
    logger.info("--- 🤖 Bot စတင်ပြင်ဆင်နေပါပြီ... ---")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    async with application:
        await application.initialize()
        await application.start()
        # တစ်နေသော စာဟောင်းများကို ဖယ်ရှားရန်
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("--- ✅ Bot is Online and Polling! ---")
        while True: await asyncio.sleep(1)

if __name__ == '__main__':
    # Flask ကို နောက်ကွယ်တွင် Run ရန်
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Telegram Bot ကို Run ရန်
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"🚨 Bot ရပ်တန့်သွားပါသည်: {e}")
