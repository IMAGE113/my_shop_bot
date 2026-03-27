import os
import logging
import asyncio
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from notion_client import Client as NotionClient
from google import genai # SDK အသစ်ကို သုံးမယ်
from google.genai import types

# --- 1. SETUP & LOGGING ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("RandysPOS")

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# Clients Init
client = genai.Client(api_key=GENAI_API_KEY)
notion = NotionClient(auth=NOTION_API_KEY)
app = Flask(__name__)

# --- 2. POS LOGIC ---
def sync_to_notion(user_name, data):
    try:
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Invoice": {"title": [{"text": {"content": f"INV-{os.urandom(2).hex().upper()}"}}]},
                "Customer": {"rich_text": [{"text": {"content": user_name}}]},
                "OrderItems": {"rich_text": [{"text": {"content": data.get("items", "N/A")}}]},
                "TotalCost": {"number": data.get("total_price", 0)},
                "Status": {"select": {"name": "Pending"}},
                "Profit": {"number": data.get("profit", 0)}
            }
        )
        return True
    except Exception as e:
        logger.error(f"Notion Error: {e}")
        return False

# --- 3. AI HANDLER ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_msg = update.message.text
    user_name = update.effective_user.first_name

    # AI Analysis using new SDK
    prompt = f"Extract POS data from: '{user_msg}'. Return JSON with items, total_price, profit."
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        order_data = json.loads(response.text)
        
        if sync_to_notion(user_name, order_data):
            await update.message.reply_text(f"✅ Order confirmed: {order_data['total_price']} MMK")
        else:
            await update.message.reply_text("❌ Database sync error.")
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text("Hi! I'm Randy's POS. How can I help you today?")

# --- 4. RUNNER ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

async def setup():
    await application.initialize()
    if WEBHOOK_URL:
        # URL မှာ double slash ဖြစ်နေတာကို ပြင်မယ်
        clean_url = WEBHOOK_URL.rstrip('/')
        await application.bot.set_webhook(f"{clean_url}/{BOT_TOKEN}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
