import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    filters
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MODEL_ID = os.getenv("MODEL_ID")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
FATEMEH_USER_ID = os.getenv("FATEMEH_USER_ID")
HISTORY_FILE = "history.txt"

headers = {
    "Authorization": f"Bearer {TOGETHER_API_KEY}",
    "Content-Type": "application/json"
}

def is_dental_related(text):
    keywords = ["tooth", "teeth", "gum", "cavity", "braces", "dentist", "floss", "implant", "mouth", "jaw", "oral"]
    return any(word in text.lower() for word in keywords)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👋 Welcome to *Witty Dentist AI*!\n\n"
        "We are here to *explain your dental problems simply* and offer suggested solutions. 🦷\n\n"
        "⚠️ *Please keep your question under 5 words!*\n"
        "Now go ahead and ask your question below 👇"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user is contacting Fatemeh before handling as normal message
    if context.user_data.get('contacting_fatemeh'):
        await forward_to_fatemeh(update, context)
        return

    user = update.effective_user
    user_id = user.id
    name = user.full_name
    username = user.username or "(no username)"
    text = update.message.text.strip()

    if not is_dental_related(text):
        await update.message.reply_text("⚠️ This bot only answers dental-related questions.")
        return

    url = "https://api.together.ai/v1/chat/completions"
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a helpful and concise dental assistant. Only return the final, short response."},
            {"role": "user", "content": text}
        ]
    }

    await update.message.reply_text("🧠 Thinking... Processing your question...")

    response = requests.post(url, headers=headers, json=payload)
    try:
        ai_response = response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        await update.message.reply_text("⚠️ Sorry, I couldn't get a valid response from the AI.")
        return

    final_text = (
        "👩‍⚕️ Hi, I'm *Fatemeh Astaraki* from *Witty Dentist AI*! 🦷\n\n"
        + ai_response +
        "\n\n🔍 _This is a suggestion only. For more accurate information, consult a dentist._"
        "\n━━━━━━━━━━━━━━━━━━━━━"
    )

    buttons = [
        [InlineKeyboardButton("🆕 Ask Another", callback_data="ask_new"), InlineKeyboardButton("📜 Last Answer", callback_data="view_last")],
        [InlineKeyboardButton("📬 Contact Fatemeh Astaraki", callback_data="contact_fatemeh")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        await update.message.reply_text(final_text, reply_markup=reply_markup, parse_mode="Markdown")
    except:
        await update.message.reply_text("⚠️ Response too long. Try a shorter question.")
        return

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"User: {name} ({user_id})\nQ: {text}\nA: {ai_response}\n{'='*40}\n")

    report = (
        "📥 *New Dental Consultation Received!*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Name:* `{name}`\n"
        f"🆔 *User ID:* `{user_id}`\n"
        f"🔗 *Username:* @{username}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ *Question:*\n{text}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Answer:*\n{ai_response}"
    )
    await context.bot.send_message(chat_id=int(GROUP_CHAT_ID), text=report, parse_mode="Markdown")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    name = user.full_name
    username = user.username or "(no username)"

    if query.data == "ask_new":
        await query.message.reply_text("📝 Please type your new question:")

    elif query.data == "view_last":
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                last = f.read().strip().split("=" * 40)[-2]
                await query.message.reply_text("📜 Last Q&A:\n" + last)
        except:
            await query.message.reply_text("❌ No previous answer found.")

    elif query.data == "contact_fatemeh":
        context.user_data['contacting_fatemeh'] = True
        await query.message.reply_text("📬 You're now contacting *Fatemeh Astaraki*!\n\n💬 Please type your question below and it will be forwarded directly.", parse_mode="Markdown")

async def forward_to_fatemeh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    name = user.full_name
    username = user.username or "(no username)"
    text = update.message.text.strip()

    context.user_data['contacting_fatemeh'] = False

    message_to_fatemeh = (
        "📩 *New Direct Message Received!*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Name:* `{name}`\n"
        f"🆔 *User ID:* `{user_id}`\n"
        f"🔗 *Username:* @{username}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *Message:*\n{text}"
    )

    await update.message.reply_text("✅ Your message has been sent to *Fatemeh Astaraki*! She will contact you as soon as possible. 🦷", parse_mode="Markdown")

    if FATEMEH_USER_ID:
        try:
            await context.bot.send_message(chat_id=int(FATEMEH_USER_ID), text=message_to_fatemeh, parse_mode="Markdown")
        except:
            pass

    await context.bot.send_message(chat_id=int(GROUP_CHAT_ID), text=message_to_fatemeh, parse_mode="Markdown")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running with Together.ai [Meta Llama 70B Free]...")
    app.run_polling()
