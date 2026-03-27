import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from notion_client import Client as NotionClient
from google import genai

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_API_KEY")
GENAI_API_KEY = os.environ.get("GENAI_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# AI Setup (New Google GenAI SDK)
client = genai.Client(api_key=GENAI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

# Notion Setup
notion = NotionClient(auth=NOTION_TOKEN)

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()

# --- HELPER FUNCTIONS ---
def get_inventory_list():
    try:
        if not DATABASE_ID:
            return "Error: NOTION_DATABASE_ID is missing in ENV!"
        response = notion.databases.query(database_id=DATABASE_ID)
        items = []
        for row in response["results"]:
            p = row["properties"]
            try:
                name = p["Product Name"]["title"][0]["plain_text"]
                price = p["Selling Price (MMK)"]["number"] or 0
                stock = p["Stock Quantity"]["number"] or 0
                items.append(f"• {name}: {price} MMK (လက်ကျန်: {stock})")
            except (KeyError, IndexError):
                continue
        return "\n".join(items) if items else "ပစ္စည်းစာရင်း မရှိသေးပါခင်ဗျာ။"
    except Exception as e:
        logging.error(f"Notion Error: {e}")
        return f"Notion Error: {str(e)}"

# --- MAIN LOGIC ---
async def process_message(user_text):
    if any(word in user_text.lower() for word in ["ဘာရှိလဲ", "menu", "list"]):
        inventory = get_inventory_list()
        return f"📋 လက်ရှိရနိုင်သော ပစ္စည်းများ:\n\n{inventory}"
    
    try:
        inventory_context = get_inventory_list()
        prompt = f"You are a shop assistant. Inventory:\n{inventory_context}\nCustomer: {user_text}"
        # google-genai SDK အသစ်ရဲ့ syntax
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "AI ဘက်က အဆင်မပြေဖြစ်နေလို့ ခဏစောင့်ပေးပါဗျာ။"

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
    return {"status": "running", "using_db": DATABASE_ID[:5] + "..." if DATABASE_ID else "None"}

@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    render_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_url:
        await tg_app.bot.set_webhook(url=f"https://{render_url}/{TOKEN}")
