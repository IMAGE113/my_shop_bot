import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import google.generativeai as genai

# ---------- Environment Variables ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
GENAI_MODEL_NAME = os.getenv("GENAI_MODEL_NAME", "gemini-1.5-turbo")
PORT = int(os.getenv("PORT", 10000))
WEB_HOOK_URL = os.getenv("WEB_HOOK_URL")

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Set API Key ----------
genai.configure(api_key=GENAI_API_KEY)
logger.info(f"Gemini API configured with model {GENAI_MODEL_NAME}")

# ---------- Telegram Bot ----------
bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# ---------- Telegram Command Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! Bot is live.")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt_text = " ".join(context.args)
    if not prompt_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a question.")
        return
    # Gemini generate
    response = genai.models.generate(
        model=GENAI_MODEL_NAME,
        prompt=prompt_text,
        max_output_tokens=300
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response.output_text)

# ---------- FastAPI Routes ----------
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    logger.info(f"Received update: {data}")
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot server is running."}

# ---------- Telegram Application ----------
def run_telegram_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ask", ask))
    # Set webhook
    bot.set_webhook(url=WEB_HOOK_URL)
    application.run_polling()

# ---------- Run FastAPI ----------
if __name__ == "__main__":
    import uvicorn
    import threading

    threading.Thread(target=run_telegram_bot, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
