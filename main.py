import os
import asyncio
import logging
import threading
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

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Model name ကို အပြည့်အစုံ 'models/gemini-1.5-flash' လို့ ရေးပေးရပါမယ်
    ai_model = genai.GenerativeModel('models/gemini-1.5-flash')

# --- [3. MESSAGE HANDLER] ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update or not update.message or not update.message.text: return
    user_text = update.message.text
    
    try:
        # AI ဆီက အဖြေတောင်းမယ်
        response = ai_model.generate_content(user_text)
        reply = response.text if response.text else "AI က အဖြေမပေးနိုင်ပါဘူး။"
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        reply = f"🚨 AI Error: {str(e)}"
    
    await update.message.reply_text(reply)

# --- [4. MAIN FUNCTION] ---
async def start_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("✅ Bot starting with models/gemini-1.5-flash...")
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
    except KeyboardInterrupt:
        pass
