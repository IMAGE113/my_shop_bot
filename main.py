import os
import logging
import asyncio
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from notion_client import Client as NotionClient
from google import genai  # SDK အသစ်

# --- 1. LOGGING SETUP ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("RandysPOS_Final")

# Configs
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# --- 2. VALIDATION & INIT ---
if not GENAI_API_KEY:
    logger.error("❌ GENAI_API_KEY is missing in Environment Variables!")

# Google GenAI Client အသစ် (API Key ကို သေချာ ထည့်သွင်းပုံ)
ai_client = genai.Client(api_key=GENAI_API_KEY) 
notion = NotionClient(auth=NOTION_API_KEY)
app = Flask(__name__)

# --- 3. CORE LOGIC ---
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
        logger.error(f"❌ Notion Sync Error: {e}")
        return False

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_msg = update.message.text
    user_name = update.effective_user.first_name

    try:
        # AI Analysis
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=f"Extract POS JSON (items, total_price, profit) from this text: '{user_msg}'. Return ONLY JSON."
        )
        
        # JSON Cleaning
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        order_data = json.loads(clean_text)
        
        if sync_to_notion(user_name, order_data):
            await update.message.reply_text(f"✅ Order Confirm: {order_data['total_price']} MMK (Saved to POS)")
    except Exception as e:
        logger.error(f"⚠️ AI/POS Error: {e}")
        await update.message.reply_text("မင်္ဂလာပါ! Randy's Cafe POS မှ ကြိုဆိုပါတယ်။ ဘာမှာယူမလဲခင်ဗျာ။")

# --- 4. FLASK & TELEGRAM RUNNER ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook process error: {e}")
        return "Error", 500

async def setup_bot():
    await application.initialize()
    if WEBHOOK_URL:
        # Webhook URL မှာ slash အပိုတွေကို ဖယ်ထုတ်မယ်
        base_url = WEBHOOK_URL.rstrip('/')
        full_webhook_path = f"{base_url}/{BOT_TOKEN}"
        await application.bot.set_webhook(full_webhook_path, drop_pending_updates=True)
        logger.info(f"🚀 Webhook Live: {full_webhook_path}")

if __name__ == "__main__":
    # Event loop အသစ်နဲ့ အလုပ်လုပ်ခြင်း
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_bot())
    # Render အတွက် Port binding
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
