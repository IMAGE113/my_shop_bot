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
def home(): return "Bot is Fully Stable!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [2. CONFIGURATION] ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Model နာမည်တွေကို အဆင့်ဆင့် ကြိုစဉ်းစားထားမယ်
MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- [3. AI RESPONSE LOGIC] ---
def get_ai_response(text):
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(text)
            return response.text
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue # နောက် model တစ်ခုနဲ့ ထပ်စမ်းမယ်
    return "🚨 လက်ရှိမှာ AI Model အားလုံး Error တက်နေပါတယ်။ ခဏနေမှ ပြန်စမ်းပေးပါ။"

# --- [4. MESSAGE HANDLER] ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # AI ဆီက အဖြေတောင်းမယ်
    reply = get_ai_response(update.message.text)
    await update.message.reply_text(reply)

# --- [5. MAIN START] ---
async def start_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("✅ Bot is Online and Ready!")
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_bot())
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
