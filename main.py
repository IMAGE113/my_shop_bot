import os
import asyncio
import logging
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. LOGGING
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. FLASK SERVER (Render Port Error အတွက် အရေးကြီးဆုံးအပိုင်း)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "OK", 200

def run_flask():
    # Render ကပေးတဲ့ Port ကို သေချာသုံးရပါမယ်
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port)

# 3. CONFIGURATION
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

# 4. MESSAGE HANDLER
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_text = update.message.text
    logger.info(f"Received message: {user_text}")

    try:
        response = ai_model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        await update.message.reply_text("ခေတ္တစောင့်ဆိုင်းပေးပါ။ AI ဘက်မှာ အလုပ်များနေလို့ပါ။")

# 5. MAIN START
async def start_bot():
    if not TOKEN:
        logger.error("No Bot Token found!")
        return

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    async with application:
        await application.initialize()
        await application.start()
        logger.info("✅ Bot logic is running...")
        await application.updater.start_polling(drop_pending_updates=True)
        # အဆုံးမရှိ စောင့်နေအောင် လုပ်ထားမယ်
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    # Flask ကို အရင်ဆုံး Background မှာ Run မယ် (Port Scan အောင်ဖို့)
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # Bot ကို Run မယ်
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
