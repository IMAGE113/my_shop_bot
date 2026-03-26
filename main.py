import os
import threading
import requests
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- [1. DUMMY WEB SERVER FOR RENDER] ---
# Render Port Error ကို ကျော်ဖို့အတွက် ဖြစ်ပါတယ်
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [2. CONFIGURATION] ---
NOTION_TOKEN = "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"
DATABASE_ID = "32f72c14272f80548ac1c464a10d92a2"
GEMINI_API_KEY = "AIzaSyDY_Y_C_O_G_1_Q_B_S_H_E_N_G_H_A_I"
TELEGRAM_BOT_TOKEN = "8630792505:AAFHcwkRWZXtAGX87-DBu7pl7j7rYPFul0k"

genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# --- [3. NOTION FUNCTIONS] ---
def get_notion_inventory():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    try:
        res = requests.post(url, headers=headers)
        data = res.json()
        items = []
        for row in data["results"]:
            name = row["properties"]["Product Name"]["title"][0]["plain_text"]
            price = row["properties"]["Selling Price"]["number"]
            items.append(f"• {name}: {price} MMK")
        return "🛍️ **လက်ရှိရနိုင်သော ပစ္စည်းများ**\n\n" + "\n".join(items) if items else "ပစ္စည်းကုန်နေပါတယ်ဗျာ။"
    except:
        return "⚠️ Notion စာရင်းဖတ်လို့မရဖြစ်နေပါတယ်။"

# --- [4. TELEGRAM HANDLER] ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if any(x in user_text.lower() for x in ["ဘာရလဲ", "menu", "ပစ္စည်း", "ဈေး"]):
        reply = get_notion_inventory()
    else:
        response = ai_model.generate_content(f"You are a friendly Burmese shop assistant: {user_text}")
        reply = response.text
    await update.message.reply_text(reply)

# --- [5. MAIN START] ---
if __name__ == '__main__':
    # Flask ကို Background မှာ run မည်
    threading.Thread(target=run_flask).start()
    
    # Telegram Bot စတင်မည်
    print("--- 🤖 Telegram Bot Starting... ---")
    tg_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    tg_app.run_polling()
