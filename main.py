import os
import asyncio
import logging
import threading
import requests
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- [1. LOGGING & SERVER] ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [2. CONFIGURATION] ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

# Gemini Setup
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Model name ကို stable ဖြစ်တဲ့ gemini-pro သို့မဟုတ် flash နဲ့ စမ်းမယ်
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
        items = [f"• {row['properties']['Product Name']['title'][0]['plain_text']}: {row['properties']['Selling Price']['number']} MMK" 
                 for row in data.get("results", []) if "Product Name" in row["properties"]]
        return "🛍️ **Menu**\n\n" + "\n".join(items) if items else "စာရင်းမရှိသေးပါ။"
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
            reply = response.text if response.text else "⚠️ AI အဖြေမပေးနိုင်ပါ။"
        except Exception as e:
            reply = f"🚨 AI Error: {str(e)}"
    
    await update.message.reply_text(reply)

# --- [5. MAIN START - RENDER FIXED] ---
if __name__ == '__main__':
    # Flask ကို Thread နဲ့ အရင်နိုးမယ်
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Telegram Bot ကို ပိုမိုခိုင်မာတဲ့ နည်းလမ်းနဲ့ Run မယ်
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("✅ Bot is starting...")
    # Render အတွက် အသင့်တော်ဆုံး polling method
    application.run_polling(drop_pending_updates=True)
