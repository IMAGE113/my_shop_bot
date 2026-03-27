# main.py
import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Notion
from notion_client import Client as NotionClient

# Gemini AI (deprecated note)
# import google.generativeai as genai  # Deprecated, switch to google.genai
# from google import genai  # Recommended

# -------------------- CONFIG --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://my-shop-bot-p2ih.onrender.com
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# -------------------- LOGGING --------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------- FLASK APP --------------------
app = Flask(__name__)

# -------------------- TELEGRAM APP --------------------
application = Application.builder().token(BOT_TOKEN).build()

# -------------------- NOTION CLIENT --------------------
notion = NotionClient(auth=NOTION_API_KEY)

# -------------------- HANDLERS --------------------
async def start(update: Update, context):
    await update.message.reply_text("Hi! I'm your test bot 😎")

async def handle_message(update: Update, context):
    user_msg = update.message.text
    user_name = update.effective_user.first_name
    logger.info(f"Received from {user_name}: {user_msg}")

    # Save to Notion
    try:
        if not DATABASE_ID:
            logger.error("❌ Notion Database ID missing!")
        else:
            notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties={
                    "Name": {"title": [{"text": {"content": user_name}}]},
                    "Order/Message": {"rich_text": [{"text": {"content": user_msg}}]},
                },
            )
            logger.info("✅ Saved to Notion successfully!")
    except Exception as e:
        logger.error(f"❌ Notion Error: {e}")

    # Gemini AI Placeholder
    try:
        # TODO: replace with google.genai Client call
        # response = genai_client.generate_content(prompt=user_msg)
        response_text = f"Echo: {user_msg}"
        await update.message.reply_text(response_text)
    except Exception as e:
        logger.error(f"❌ Gemini Error: {e}")
        await update.message.reply_text("AI Error ❌")

# -------------------- ADD HANDLERS --------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------- FLASK WEBHOOK ROUTE --------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    """Telegram Webhook endpoint"""
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

# -------------------- STARTUP FUNCTION --------------------
async def startup():
    """Initialize Application and set webhook"""
    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    logger.info(f"Webhook set to: {WEBHOOK_URL}/{BOT_TOKEN}")

# -------------------- RUN FLASK --------------------
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(startup())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=True)
