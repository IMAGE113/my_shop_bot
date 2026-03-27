import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot
from telegram.ext import Dispatcher, MessageHandler, filters
import google.generativeai as genai
import requests

# ---------------------
# Config
# ---------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

genai.api_key = GENAI_API_KEY

bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

logging.basicConfig(level=logging.INFO)

# ---------------------
# Notion Helper
# ---------------------
def get_inventory_list():
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    data = response.json()
    items = []
    for result in data.get("results", []):
        props = result["properties"]
        name = props["Product Name"]["title"][0]["text"]["content"] if props["Product Name"]["title"] else "Unknown"
        price = props["Selling Price"]["number"] if props["Selling Price"]["number"] else 0
        stock = props["Stock Quantity"]["number"] if props["Stock Quantity"]["number"] else 0
        category = props["Category"]["select"]["name"] if props.get("Category") and props["Category"]["select"] else "None"
        items.append(f"{name} - {price} MMK ({stock} left) [{category}]")
    return "\n".join(items) if items else "No items in stock."

# ---------------------
# AI Helper
# ---------------------
def ai_response(user_text):
    inventory = get_inventory_list()
    prompt = f"""
You are an AI assistant for Randy's Cafe.
Here is the current inventory:\n{inventory}\n
Customer says: {user_text}
Reply politely and suggest items from the inventory.
"""
    response = genai.chat.completions.create(
        model="gemini-1.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for a cafe."},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].content

# ---------------------
# Telegram Webhook
# ---------------------
@app.post("/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN:
        return {"status": "unauthorized"}
    update = await request.json()
    logging.info(f"Received update: {update}")

    chat_id = update["message"]["chat"]["id"]
    text = update["message"]["text"]

    if text.lower() in ["ဘာရှိလဲ", "menu", "မူနူး"]:
        reply = get_inventory_list()
    else:
        reply = ai_response(text)

    bot.send_message(chat_id=chat_id, text=reply)
    return {"status": "ok"}
