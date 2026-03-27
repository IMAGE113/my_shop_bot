import os
import asyncio
import threading
import requests
import logging
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- [1. LOGGING & SERVER] ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Fixed and Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [2. CONFIGURATION] ---
TELEGRAM_BOT_TOKEN = "8630792505:AAFHcwkRWZXtAGX87-DBu7pl7j7rYPFul0k"
GEMINI_API_KEY = "AIzaSyD1LSZZ0gxep7ol4fItYDuDtkJddQ_H6tw"
NOTION_TOKEN = "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"
DATABASE_ID = "32f72c14272f80548ac1c464a10d92a2"

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)

# ChatGPT အကြံပြုချက်အရ ပိုပြီး Stable ဖြစ်တဲ့ Model နာမည်ကို သုံးပါမယ်
# တကယ်လို့ 1.5-flash မရရင် 'gemini-pro' ကို အလိုအလျောက် ပြောင်းသုံးဖို့ Logic ထည့်ပေးထားတယ်
try:
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except:
    ai_model = genai.GenerativeModel('gemini-pro')

# --- [3. NOTION FUNCTION] ---
def get_notion_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    try:
        res = requests.post(url, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()
        items = [f"• {row['properties']['Product Name']['title'][0]['plain_text']}: {row['properties']['Selling Price']['number']} MMK" 
                 for row in data.get("results", []) if "Product Name" in row["properties"]]
        return "🛍️ **လက်ရှိရောင်းရန်ပစ္စည်းများ**\n\n" + "\n".join(items) if items else "စာရင်းအလွတ်ဖြစ်နေပါတယ်။"
    except Exception as e:
        return f"⚠️ Notion Error: {str(e)}"

# --- [4. MESSAGE HANDLER] ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    
    if any(kw in user_text.lower() for kw in ["menu", "ဈေး", "ဘာရလဲ"]):
        reply = get_notion_data()
    else:
        try:
            # AI ကို ခေါ်တဲ့အခါ model error တက်ရင် သိနိုင်အောင် debug ထည့်ထားတယ်
            response = ai_model.generate_content(user_text)
            reply = response.text
        except Exception as e:
            logger.error(f"AI Error: {e}")
            reply = f"🚨 AI ခဏနားနေပါတယ်။ (Error: {str(e)})"
    
    await update.message.reply_text(reply)

# --- [5. MAIN START] ---
def main():
    # ChatGPT အကြံပေးသလို polling စနစ်ကို ပိုခိုင်မာအောင် ပြင်မယ်
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Flask ကို thread နဲ့ run မယ်
    threading.Thread(target=run_flask, daemon=True).start()
    
    logger.info("--- ✅ Bot is Starting with run_polling()... ---")
    # application.run_polling() က ပိုပြီး stable ဖြစ်ပါတယ်
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
