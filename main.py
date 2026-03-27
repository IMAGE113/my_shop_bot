import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import httpx
import google.generativeai as genai
from notion_client import Client as NotionClient

# =========================
# Config / Environment
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
NOTION_KEY = os.getenv("NOTION_KEY")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

# Gemini client init (stable 0.4.1)
client = genai.Client(api_key=GENAI_API_KEY)

# Notion client
notion = NotionClient(auth=NOTION_KEY)

# Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

# =========================
# Telegram Handlers
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # Call Gemini
    try:
        response = client.generate_text(
            model="text-bison-001",
            prompt=user_text,
            temperature=0.7,
            max_output_tokens=500
        )
        reply_text = response.result
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        reply_text = "Sorry, something went wrong with AI."

    # Send reply
    await update.message.reply_text(reply_text)

    # Log to Notion (optional)
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "Question": {"title": [{"text": {"content": user_text}}]},
                "Answer": {"rich_text": [{"text": {"content": reply_text}}]},
            },
        )
    except Exception as e:
        logging.error(f"Notion Error: {e}")

# Telegram app
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# =========================
# FastAPI webhook
# =========================
@app.post(f"/{TELEGRAM_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await telegram_app.update_queue.put(update)
    return {"ok": True}

# =========================
# Run
# =========================
if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
