import os
import asyncio
import logging
import threading
import requests
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- [1. LOGGING & SERVER SETUP] ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [2. CONFIGURATION] ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-pro')

# --- [3. NOTION DATA FUNCTION] ---
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
                name = row["properties"]["Product Name"]["title"][0]["plain_text"]
                price = row["properties"]["Selling Price"]["number"]
                items.append(f"• {name}: {price} MMK")
            except: continue
        return "🛍️ **Shop Menu**\n\n" + "\n".join(items) if items else "စာရင်းမရှိသေးပါ။"
    except Exception as e:
        return f"⚠️ Notion Error: {str(e)}"

# --- [4. MESSAGE HANDLER] ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update or not update.message or not update.message.text: return
    user_text = update.message.text
    
    if any(kw in user_text.lower() for kw in ["menu", "ဈေး", "ဘာရလဲ"]):
        reply = get_notion_data()
    else:
        try:
            response = ai_model.generate_content(user_text)
            reply = response.text if response.text else "AI က အဖြေမပေးနိုင်ပါဘူး။"
        except Exception as e:
            reply = f"🚨 AI Error: {str(e)}"
    
    await update.message.reply_text(reply)

# --- [5. FIX FOR RUNTIME ERROR - EVENT LOOP] ---
async def start_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("✅ Telegram Bot is Starting...")
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        # Bot ကို အမြဲတမ်း ပွင့်နေအောင် စောင့်ခိုင်းထားမယ်
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    # Flask ကို Thread နဲ့ run မယ်
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Python 3.14 Event Loop ပြဿနာအတွက် asyncio.run ကို သုံးမယ်
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
