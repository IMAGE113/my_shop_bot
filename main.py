import logging
import requests
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- [CONFIGURATION - အကုန်လုံး ဖြည့်စွက်ပြီးသား] ---
NOTION_TOKEN = "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"
DATABASE_ID = "32f72c14272f80548ac1c464a10d92a2"
GEMINI_API_KEY = "AIzaSyDY_Y_C_O_G_1_Q_B_S_H_E_N_G_H_A_I"
TELEGRAM_BOT_TOKEN = "8630792505:AAFHcwkRWZXtAGX87-DBu7pl7j7rYPFul0k"

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# Notion မှ ပစ္စည်းစာရင်းယူသည့် Function
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
            # Product Name နှင့် Selling Price Column များမှ Data ယူခြင်း
            name = row["properties"]["Product Name"]["title"][0]["plain_text"]
            price = row["properties"]["Selling Price"]["number"]
            items.append(f"• {name}: {price} MMK")
        return "🛍️ **လက်ရှိရနိုင်သော ပစ္စည်းများ**\n\n" + "\n".join(items) if items else "ပစ္စည်းကုန်နေပါတယ်ဗျာ။"
    except Exception as e:
        return f"⚠️ Notion Error: {str(e)}"

# Telegram မှ စာဝင်လာလျှင် တုံ့ပြန်မည့် Function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    print(f"Customer sent: {user_text}")

    # ဝယ်သူက ပစ္စည်းစာရင်း သို့မဟုတ် စျေးနှုန်းမေးလျှင်
    if any(x in user_text.lower() for x in ["ဘာရလဲ", "menu", "ပစ္စည်း", "ဈေး", "price"]):
        reply = get_notion_inventory()
    # ကျန်တာဆိုလျှင် Gemini AI ကို ဖြေခိုင်းမည်
    else:
        system_instruction = "You are a friendly Burmese shop assistant. Answer politely in Burmese language."
        response = ai_model.generate_content(f"{system_instruction}\nCustomer: {user_text}")
        reply = response.text

    await update.message.reply_text(reply)

if __name__ == '__main__':
    print("--- 🤖 Your Smart Shop Bot is STARTING... ---")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Bot ကို စတင်လည်ပတ်စေခြင်း
    app.run_polling()
