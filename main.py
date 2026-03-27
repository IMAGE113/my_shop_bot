import os
import logging
import asyncio
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from notion_client import Client as NotionClient
from google import genai 

# --- CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RandysPOS")

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GEMINI_KEY = os.getenv("GEMINI-API_KEY")

# Init Clients
ai_client = genai.Client(api_key=GEMINI_KEY)
notion = NotionClient(auth=NOTION_API_KEY)
app = Flask(__name__)

# Build Application
application = Application.builder().token(BOT_TOKEN).build()

# --- NOTION SYNC ---
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

# --- MESSAGE HANDLER ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_msg = update.message.text
    user_name = update.effective_user.first_name

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=f"Extract POS JSON (items, total_price, profit) from: {user_msg}. Return ONLY JSON."
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        order_data = json.loads(clean_text)
        
        if sync_to_notion(user_name, order_data):
            await update.message.reply_text(f"✅ Order confirmed: {order_data['items']}\n💰 Total: {order_data['total_price']} MMK")
    except Exception as e:
        logger.error(f"AI/POS Error: {e}")
        await update.message.reply_text("မင်္ဂလာပါ! Randy's Cafe POS မှ ကြိုဆိုပါတယ်။ ဘာမှာယူမလဲခင်ဗျာ။")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))

# --- FLASK & WEBHOOK ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    # Flask[async] သုံးထားလို့ await တိုက်ရိုက်လုပ်လို့ရပြီ
    await application.process_update(update)
    return "OK", 200

async def setup():
    await application.initialize()
    if WEBHOOK_URL:
        base_url = WEBHOOK_URL.rstrip('/')
        await application.bot.set_webhook(f"{base_url}/{BOT_TOKEN}")

if __name__ == "__main__":
    # Webhook setup လုပ်မယ်
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
    
    # Flask run မယ်
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
