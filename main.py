import os
import logging
import asyncio
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from notion_client import Client as NotionClient
from google import genai 

# --- 1. LOGGING & CONFIG ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger("RandysPOS_Final")

# Render Environment Variables တွေကို ဆွဲယူမယ်
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY") # မင်းပေးထားတဲ့ နာမည်အတိုင်း အတိအကျ

# --- 2. VALIDATION ---
if not all([BOT_TOKEN, GENAI_API_KEY, NOTION_API_KEY, DATABASE_ID]):
    logger.error("❌ Environment Variables တစ်ခုခု လိုအပ်နေပါတယ်! Render Dashboard မှာ ပြန်စစ်ပေးပါ။")

# Init Clients
ai_client = genai.Client(api_key=GENAI_API_KEY)
notion = NotionClient(auth=NOTION_API_KEY)
app = Flask(__name__)

# Build Telegram Application
application = Application.builder().token(BOT_TOKEN).build()

# --- 3. NOTION SYNC ENGINE ---
def sync_to_notion(user_name, data):
    try:
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Invoice": {"title": [{"text": {"content": f"INV-{os.urandom(2).hex().upper()}"}}]},
                "Customer": {"rich_text": [{"text": {"content": user_name}}]},
                "OrderItems": {"rich_text": [{"text": {"content": data.get("items", "N/A")}}]},
                "TotalCost": {"number": float(data.get("total_price", 0))},
                "Status": {"select": {"name": "Pending"}},
                "Profit": {"number": float(data.get("profit", 0))}
            }
        )
        return True
    except Exception as e:
        logger.error(f"❌ Notion Sync Error: {e}")
        return False

# --- 4. MESSAGE HANDLER (AI LOGIC) ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_msg = update.message.text
    user_name = update.effective_user.first_name

    # AI စဉ်းစားနေတုန်း Typing... ပြမယ်
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Gemini AI ဆီကနေ JSON Format နဲ့ Data ထုတ်ခိုင်းမယ်
        prompt = (
            f"Extract order details from this message: '{user_msg}'. "
            "Return ONLY a JSON object with keys: 'items' (string), "
            "'total_price' (number), 'profit' (number, calculated as 30% of total)."
        )
        
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt
        )
        
        # JSON ကို သန့်စင်မယ်
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        order_data = json.loads(clean_text)
        
        # Notion ထဲကို သိမ်းမယ်
        if sync_to_notion(user_name, order_data):
            msg = (
                f"✅ Order အောင်မြင်ပါတယ် {user_name} ခင်ဗျာ!\n"
                f"☕️ မှာယူမှု: {order_data['items']}\n"
                f"💰 စုစုပေါင်း: {order_data['total_price']} MMK"
            )
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("⚠️ Notion နဲ့ ချိတ်ဆက်ရတာ အဆင်မပြေဖြစ်နေပါတယ်။")

    except Exception as e:
        logger.error(f"⚠️ AI/POS Error: {e}")
        await update.message.reply_text("မင်္ဂလာပါ! Randy's Cafe POS မှ ကြိုဆိုပါတယ်။ ဘာမှာယူမလဲခင်ဗျာ။")

# Handler ကို Register လုပ်မယ်
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))

# --- 5. WEBHOOK & RUNNER ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

async def setup():
    await application.initialize()
    if WEBHOOK_URL:
        base_url = WEBHOOK_URL.rstrip('/')
        await application.bot.set_webhook(f"{base_url}/{BOT_TOKEN}")
        logger.info(f"🚀 Webhook set at: {base_url}/{BOT_TOKEN}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
    
    # Render Port မှာ Run မယ်
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
