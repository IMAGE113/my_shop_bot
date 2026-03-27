import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from notion_client import Client
import google.generativeai as genai

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_API_KEY")
GENAI_API_KEY = os.environ.get("GENAI_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# --- SETUP ---
logging.basicConfig(level=logging.INFO)

# Gemini (Stable SDK)
genai.configure(api_key=GENAI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"  # Stable SDK မှာသုံးနိုင်ပါတယ်

# Notion
notion = Client(auth=NOTION_TOKEN)

# FastAPI + Telegram
app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()

# --- NOTION INVENTORY ---
def get_inventory_list():
    try:
        if not DATABASE_ID:
            return "❌ Database ID missing"

        response = notion.databases.query(database_id=DATABASE_ID)

        items = []
        for row in response.get("results", []):
            props = row.get("properties", {})

            # Product Name
            title_data = props.get("Product Name", {}).get("title", [])
            name = title_data[0]["plain_text"] if title_data else "Unknown"

            # Price
            price = props.get("Selling Price (MMK)", {}).get("number") or 0

            # Stock
            stock = props.get("Stock Quantity", {}).get("number") or 0

            items.append(f"• {name} - {price} MMK (Stock: {stock})")

        return "\n".join(items) if items else "No items found."

    except Exception as e:
        logging.error(f"Notion Error: {e}")
        return "⚠️ Database error"

# --- AI RESPONSE ---
async def process_message(user_text):
    # Menu trigger
    if any(word in user_text.lower() for word in ["menu", "list", "ဘာရှိလဲ"]):
        inventory = get_inventory_list()
        return f"📋 Randy's Shop Menu:\n\n{inventory}"

    try:
        inventory = get_inventory_list()

        prompt = f"""
You are a helpful shop assistant.

Available products:
{inventory}

Customer: {user_text}

Reply naturally and recommend products if needed.
"""

        response = genai.models.generate(
            model=MODEL_NAME,
            prompt=prompt,
            max_output_tokens=500
        )

        return response.output_text if response.output_text else "🤖 No response"

    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "⚠️ AI error, try again later"

# --- TELEGRAM WEBHOOK ---
@app.post(f"/{TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)

    if update.message and update.message.text:
        reply = await process_message(update.message.text)

        await tg_app.bot.send_message(
            chat_id=update.effective_chat.id,
            text=reply
        )

    return {"status": "ok"}

# --- HEALTH CHECK ---
@app.get("/")
async def home():
    return {"status": "running"}

# --- STARTUP ---
@app.on_event("startup")
async def startup():
    await tg_app.initialize()

    render_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_url:
        webhook_url = f"https://{render_url}/{TOKEN}"
        await tg_app.bot.set_webhook(webhook_url)
        logging.info(f"Webhook set: {webhook_url}")
