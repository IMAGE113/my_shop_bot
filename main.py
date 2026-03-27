import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from notion_client import Client
from google import genai

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_API_KEY")
GENAI_API_KEY = os.environ.get("GENAI_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# AI Setup - Model နာမည်အပြည့်အစုံသုံးမယ်
client = genai.Client(api_key=GENAI_API_KEY)
MODEL_NAME = "models/gemini-1.5-flash"

# Notion Setup
notion = Client(auth=NOTION_TOKEN)

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()

# --- HELPER FUNCTIONS ---
def get_inventory_list():
    try:
        if not DATABASE_ID:
            return "Error: NOTION_DATABASE_ID missing!"
        
        # Notion query format ကို သေချာအောင် ပြင်ထားတယ်
        response = notion.databases.query(**{"database_id": DATABASE_ID})
        items = []
        for row in response.get("results", []):
            p = row.get("properties", {})
            try:
                # Column နာမည်တွေဖြစ်တဲ့ Product Name, Selling Price (MMK), Stock Quantity
                name_data = p.get("Product Name", {}).get("title", [])
                name = name_data[0].get("plain_text") if name_data else "Unknown"
                
                price = p.get("Selling Price (MMK)", {}).get("number") or 0
                stock = p.get("Stock Quantity", {}).get("number") or 0
                
                items.append(f"• {name}: {price} MMK (Stock: {stock})")
            except Exception:
                continue
        return "\n".join(items) if items else "No items found."
    except Exception as e:
        logging.error(f"Notion Error: {e}")
        return "Database အလုပ်မလုပ်သေးပါခင်ဗျာ။"

# --- MAIN LOGIC ---
async def process_message(user_text):
    if any(word in user_text.lower() for word in ["ဘာရှိလဲ", "menu", "list"]):
        inventory = get_inventory_list()
        return f"📋 **Randy's Cafe Menu:**\n\n{inventory}"
    
    try:
        inventory_context = get_inventory_list()
        prompt = f"You are a helpful shop assistant. Context:\n{inventory_context}\nCustomer: {user_text}"
        # Gemini syntax ကို model_name အမှန်နဲ့ ပြင်ထားတယ်
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "AI နားမလည်လို့ ခဏစောင့်ပေးပါဗျာ။"

# --- ROUTES ---
@app.post(f"/{TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    if update.message and update.message.text:
        reply_text = await process_message(update.message.text)
        await tg_app.bot.send_message(chat_id=update.effective_chat.id, text=reply_text)
    return {"status": "ok"}

@app.get("/")
async def health_check():
    return {"status": "running"}

@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    render_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_url:
        await tg_app.bot.set_webhook(url=f"https://{render_url}/{TOKEN}")
