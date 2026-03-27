import os
import json
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from notion_client import Client as NotionClient
from google import genai

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GENAI_API_KEY = os.getenv("GENAI_API_KEY") 
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

notion = NotionClient(auth=NOTION_API_KEY)
ai_client = genai.Client(api_key=GENAI_API_KEY)
application = Application.builder().token(BOT_TOKEN).build()
app = FastAPI()

# --- 1. FETCH FROM NOTION ---
async def fetch_inventory():
    # Notion Version အသစ်အတွက် query logic
    response = notion.databases.query(database_id=DATABASE_ID)
    inventory = {}
    for page in response["results"]:
        p = page["properties"]
        # မင်းရဲ့ Screenshot ထဲက Column နာမည်တွေနဲ့ ညှိထားတယ်
        name = p["Product Name"]["title"][0]["plain_text"]
        inventory[name] = {
            "id": page["id"],
            "stock": p["Stock Quantity"]["number"] or 0,
            "orders": p["Total Orders"]["number"] or 0,
            "price": p["Selling Price (MMK)"]["number"] or 0
        }
    return inventory

# --- 2. UPDATE NOTION ---
async def update_notion_stock(page_id, new_stock, new_orders):
    notion.pages.update(
        page_id=page_id,
        properties={
            "Stock Quantity": {"number": new_stock},
            "Total Orders": {"number": new_orders}
        }
    )

# --- 3. AI PROCESSOR ---
async def process_order(user_text):
    inventory = await fetch_inventory()
    inv_summary = {n: {"stock": d["stock"], "price": d["price"]} for n, d in inventory.items()}
    
    prompt = f"User: '{user_text}'. Inventory: {json.dumps(inv_summary)}. Return JSON {{'match': true/false, 'item': 'name', 'qty': 1}}."
    
    response = ai_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    order = json.loads(response.text.replace("```json", "").replace("```", "").strip())

    if order.get("match") and order["item"] in inventory:
        item = inventory[order["item"]]
        if item["stock"] >= order["qty"]:
            new_stock = item["stock"] - order["qty"]
            new_orders = item["orders"] + order["qty"]
            
            await update_notion_stock(item["id"], new_stock, new_orders)
            return f"✅ {order['item']} အတွက် Order တင်ပြီးပါပြီ!\n📦 လက်ကျန်စတော့: {new_stock}\n📊 စုစုပေါင်းရောင်းရမှု: {new_orders}"
        return f"❌ {order['item']} က စတော့ကုန်နေပါတယ် (လက်ကျန်: {item['stock']})"
    return "❓ နားမလည်ပါဘူးခင်ဗျာ။ ပစ္စည်းနာမည်ကို သေချာပြောပေးပါ။"

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    if update.message and update.message.text:
        reply = await process_order(update.message.text)
        await application.bot.send_message(chat_id=update.effective_chat.id, text=reply)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
