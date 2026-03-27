import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from notion_client import Client # Notion Library ပြန်ထည့်မယ်

# --- Config ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# --- Clients Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GENAI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")
notion = Client(auth=NOTION_TOKEN)

app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Notion Helper ---
def save_to_notion(user_name, message):
    try:
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": user_name}}]},
                "Order/Message": {"rich_text": [{"text": {"content": message}}]},
            },
        )
        logger.info("✅ Saved to Notion successfully!")
    except Exception as e:
        logger.error(f"❌ Notion Error: {e}")

# --- Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_msg = update.message.text
    user_name = update.message.from_user.first_name
    logger.info(f"Received from {user_name}: {user_msg}")

    # 1. Save to Notion (Order တွေကို မှတ်မယ်)
    save_to_notion(user_name, user_msg)

    # 2. Get AI Response
    try:
        response = ai_model.generate_content(user_msg)
        reply_text = response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        reply_text = "AI ခေတ္တ အနားယူနေပါတယ်။"

    await update.message.reply_text(reply_text)

application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# --- Webhook & Startup (Same as before) ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

@app.route("/")
def index(): return "Bot is running with Notion & Webhook!", 200

async def set_webhook():
    if WEBHOOK_URL and BOT_TOKEN:
        webhook_path = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        await application.bot.set_webhook(url=webhook_path, drop_pending_updates=True)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
