import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
import google.generativeai as genai
import httpx

# ---------- Environment Variables ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
GENAI_MODEL_NAME = os.getenv("GENAI_MODEL_NAME", "gemini-1.5-turbo")
PORT = int(os.getenv("PORT", 10000))
WEB_HOOK_URL = os.getenv("WEB_HOOK_URL")

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Initialize Telegram Bot ----------
bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# ---------- Initialize Gemini AI Client ----------
client = genai.Client(api_key=GENAI_API_KEY)
logger.info(f"Gemini client initialized with model {GENAI_MODEL_NAME}")

# ---------- Telegram Command Handler ----------
async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! Bot is live.")

# ---------- FastAPI Routes ----------
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    logger.info(f"Received update: {data}")
    # process incoming update here if needed
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot server is running."}

# ---------- Telegram Application ----------
def run_telegram_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    # Set webhook
    bot.set_webhook(url=WEB_HOOK_URL)
    application.run_polling()

# ---------- Start FastAPI Server ----------
if __name__ == "__main__":
    import uvicorn
    import threading

    # Run Telegram bot in separate thread
    threading.Thread(target=run_telegram_bot, daemon=True).start()
    
    # Run FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=PORT)
