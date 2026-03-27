import os
import logging
import asyncio
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from notion_client import Client as NotionClient
import google.generativeai as genai

# -------------------- 1. DEBUG LOGGING --------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger("RandysPOS_Debug")

# Environment Variables စစ်ဆေးခြင်း
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# -------------------- 2. SERVICES INIT --------------------
genai.configure(api_key=GENAI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")
notion = NotionClient(auth=NOTION_API_KEY)
app = Flask(__name__)

# -------------------- 3. FUTURE PAYMENT INTEGRATION --------------------
class PaymentGateway:
    """MayanPay API ချိတ်ဖို့ အသင့်ပြင်ထားတဲ့ နေရာ"""
    @staticmethod
    async def get_payment_url(amount):
        # TODO: MayanPay API call logic here
        return f"https://mayanpay.com.mm/checkout?amt={amount}"

# -------------------- 4. NOTION POS ENGINE --------------------
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
                "PaymentType": {"select": {"name": data.get("payment_type", "COD")}},
                "Deli": {"select": {"name": data.get("delivery", "Standard")}},
                "Profit": {"number": data.get("profit", 0)}
            }
        )
        return True
    except Exception as e:
        logger.error(f"❌ Notion Error: {e}")
        return False

# -------------------- 5. AI DATA EXTRACTOR --------------------
async def extract_order_info(text):
    prompt = f"""
    Strict POS Extraction. User input: "{text}"
    Return ONLY JSON:
    {{
      "items": "string",
      "total_price": number,
      "payment_type": "Prepaid/COD",
      "delivery": "Deli/Pickup",
      "profit": number (total * 0.3)
    }}
    If not an order, return {{"error": "true"}}.
    """
    try:
        response = ai_model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"❌ AI Error: {e}")
        return None

# -------------------- 6. CORE HANDLER --------------------
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_msg = update.message.text
    user_name = update.effective_user.first_name
    logger.info(f"📩 From {user_name}: {user_msg}")

    # AI Analysis
    order_data = await extract_order_info(user_msg)

    if not order_data or "error" in order_data:
        await update.message.reply_text(f"မင်္ဂလာပါ {user_name}! Randy's Cafe POS မှ ကြိုဆိုပါတယ်။ ဘာမှာယူလိုပါသလဲခင်ဗျာ။")
        return

    # Sync to Notion
    if sync_to_notion(user_name, order_data):
        pay_url = await PaymentGateway.get_payment_url(order_data['total_price'])
        msg
