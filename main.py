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
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# Init Clients
ai_client = genai.Client(api_key=GENAI_API_KEY)
notion = NotionClient(auth=NOTION_API_KEY)
app = Flask(__name__)

# Build Application
application = Application.builder().token(BOT_TOKEN).build()

# --- HANDLER ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update or not update.message or not update.message.text: return
    user_msg = update.message.text
    user_name = update.effective_user.first_name

    try:
        # AI Processing
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=f"Extract POS JSON from: {user_msg}. Return ONLY JSON."
        )
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        order_data = json.loads(clean_text)
        
        # Order confirm message
        await update.message.reply_text(f"✅ AI Confirmed: {order_data['items']} ({order_data['total_price']} MMK)")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("မင်္ဂလာပါ! Randy's Cafe POS မှ ကြိုဆိုပါတယ်။")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))

# --- WEBHOOK ROUTE (The Fix) ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    # Flask[async] ရဲ့ အားသာချက်ကို ယူပြီး await တိုက်ရိုက်လုပ်မယ်
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        # ဒီနေရာမှာ application ကို initialize လုပ်ထားပြီးသားဖြစ်ရမယ်
        await application.process_update(update)
        return "OK", 200
    return "Forbidden", 403

# Initialize application once
async def init_bot():
    await application.initialize()
    if WEBHOOK_URL:
        url = f"{WEBHOOK_URL.rstrip('/')}/{BOT_TOKEN}"
        await application.bot.set_webhook(url)
        logger.info(f"Webhook set to {url}")

# Render အတွက် Port ချိတ်ဆက်မှု
if __name__ == "__main__":
    # Asyncio loop ကို ပိတ်မသွားအောင် ထိန်းမယ်
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_bot())
    
    # Flask ကို async mode နဲ့ run မယ်
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
