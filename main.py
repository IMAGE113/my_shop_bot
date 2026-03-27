# main.py
import os
from fastapi import FastAPI, Request
from telegram import Bot
from google.generativeai import Client as GeminiClient
from notion_client import Client as NotionClient

# ------------------------
# Environment / Config
# ------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# ------------------------
# Initialize Clients
# ------------------------
bot = Bot(token=TELEGRAM_TOKEN)
notion = NotionClient(auth=NOTION_API_KEY)
gemini = GeminiClient(api_key=GENAI_API_KEY)

# ------------------------
# FastAPI App
# ------------------------
app = FastAPI()

# ------------------------
# Helper Functions
# ------------------------
def get_inventory_list():
    results = notion.databases.query(database_id=NOTION_DB_ID)
    menu = []
    for page in results['results']:
        name = page['properties']['Product Name']['title'][0]['plain_text']
        price = page['properties']['Selling Price (MMK)']['number']
        stock = page['properties']['Stock Quantity']['number']
        category = page['properties']['Category']['select']['name'] if page['properties']['Category']['select'] else "No Category"
        menu.append(f"{name} ({category}) - {price} MMK ({stock} left)")
    return "\n".join(menu)

def ai_reply(message_text):
    with open("prompt.txt", "r") as f:
        base_prompt = f.read()
    prompt = base_prompt + f"\nCustomer says: {message_text}"
    response = gemini.chat(messages=[{"role": "user", "content": prompt}], model="gemini-1.5-turbo")
    return response['content'][0]['text'] if 'content' in response else "Sorry, cannot answer."

# ------------------------
# Telegram Webhook
# ------------------------
@app.post("/{token}")
async def telegram_webhook(token: str, req: Request):
    if token != TELEGRAM_TOKEN:
        return {"status": "unauthorized"}
    
    data = await req.json()
    if "message" in data and "text" in data["message"]:
        text = data["message"]["text"]
        chat_id = data["message"]["chat"]["id"]

        if text.lower() in ["menu", "ဘာရှိလဲ"]:
            reply = get_inventory_list()
        else:
            reply = ai_reply(text)

        bot.send_message(chat_id=chat_id, text=reply)
    return {"status": "ok"}

# ------------------------
# Test Endpoint
# ------------------------
@app.get("/")
async def home():
    return {"status": "AI POS System is running!"}
