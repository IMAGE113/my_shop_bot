async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_msg = update.message.text
    
    # AI အလုပ်လုပ်နေပြီဆိုတာ သိအောင် Typing ပို့ထားမယ်
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # AI Analysis (timeout ထည့်ထားမယ်)
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=f"Extract POS JSON (items, total_price, profit) from: {user_msg}. Return ONLY JSON."
        )
        
        if response and response.text:
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            order_data = json.loads(clean_text)
            
            # AI အဖြေပေးနိုင်ရင် ဒီစာ ထွက်လာမယ်
            await update.message.reply_text(f"✅ AI က ဖတ်လိုက်ပြီ- {order_data['items']} (စုစုပေါင်း {order_data['total_price']} ကျပ်)")
        else:
            raise ValueError("AI Response is empty")

    except Exception as e:
        logger.error(f"AI Error: {e}")
        # AI အလုပ်မလုပ်ရင် ဒီ Default စာ ထွက်လာမှာပါ
        await update.message.reply_text("AI ခေတ္တ အနားယူနေပါတယ်။ စာသားကို သေချာ ပြန်ရေးပေးပါဦး။")
