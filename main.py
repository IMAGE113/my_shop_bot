import os
import json
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from notion_client import Client as NotionClient
from google import genai

# --- CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RandyOmniPOS")

# မင်းပေးထားတဲ့ နာမည်တွေအတိုင်း အတိအကျယူမယ်
BOT_TOKEN = os.getenv("BOT_TOKEN")
GENAI_API_KEY = os.getenv("GENAI_API_KEY") 
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Clients Initialize
notion = NotionClient(auth=NOTION_API_KEY)
ai_client = genai.Client(api_key=GENAI_API_KEY)
application = Application.builder().token(BOT_TOKEN).build()

app = FastAPI()

# --- 1. NOTION ကနေ စာရင်းဆွဲထုတ်မယ် ---
async def fetch_inventory():
    response = notion.databases.query(database_id=DATABASE_ID)
    inventory = {}
    for page in response["results"]:
        p = page["properties"]
        # မင်း Notion မှာ ဆောက်ထားတဲ့ Column နာမည်တွေနဲ့ အံကိုက်ဖြစ်ရမယ်
        name = p["Item Name"]["title"][0]["plain_text"]
        inventory[name] = {
            "id": page["id"],
            "stock": p["Stock"]["number"] or 0,
            "price": p["Selling Price"]["number"] or 0,
            "cost": p["Cost Price"]["number"] or 0
        }
    return inventory

# --- 2. AI LOGIC (ပစ္စည်းရှာ၊ စတော့စစ်၊ အမြတ်တွက်) ---
async def process_order(user_text):
    inventory = await fetch_inventory()
    
    # AI ဆီကို လက်ရှိ Stock အခြေအနေ ပို့ပေးမယ်
    inv_summary = {n: {"stock": d["stock"], "price": d["price"]} for n, d in inventory.items()}
    
    prompt = f"""
    User says: "{user_text}"
    Available Items: {json.dumps(inv_summary)}
    
    If they want to buy, return ONLY JSON: 
    {{"match": true, "item": "exact_name", "qty": 1}}
    If not found, return: {{"match": false}}
    """
    
    response = ai_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    order = json.loads(response.text.replace("```json", "").replace("```", "").strip())

    if order.get("match") and order["item"] in inventory:
        target = inventory[order["item"]]
        if target["stock"] >= order["qty"]:
            # စတော့နှုတ်မယ်
            new_stock = target["stock"] - order["qty"]
            # အမြတ်တွက်မယ် (Selling - Cost)
            profit = (target["price"] - target["cost"]) * order["qty"]
            
            # Notion မှာ သွားပြင်မယ်
            notion.pages.update(
                page_id=target["id"],
                properties={"Stock": {"number": new_stock}}
            )
            return f"✅ Order Confirmed!\n☕️ {order['item']} x{order['qty']}\n📦 ကျန်စတော့: {new_stock}\n💰 အမြတ်: {profit} MMK"
        return f"❌ {order['item']} က စတော့မလောက်တော့ပါဘူး (လက်ကျန်: {target['stock']})"
    
    return "❓ စာရင်းထဲမှာ မရှိတဲ့ပစ္စည်းဖြစ်နေပါတယ်၊ ပြန်စစ်ပေးပါဦး။"

# --- 3. TELEGRAM WEBHOOK ROUTE ---
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    
    if update.message and update.message.text:
        result_msg = await process_order(update.message.text)
        await application.bot.send_message(chat_id=update.effective_chat.id, text=result_msg)
    
    return {"status": "ok"}

# --- 4. SERVER RUNNER ---
if __name__ == "__main__":
    import uvicorn
    # Render မှာ run ဖို့ port ချိတ်မယ်
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
