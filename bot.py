# CVise Telegram Bot Project (with PDF-only results)

import os
import logging
import tempfile
from telegram import Update, ReplyKeyboardMarkup, Document
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from analyzer import (
    extract_text_from_file,
    analyze_resume,
    analyze_for_vacancy,
    give_hr_feedback,
    generate_cover_letter,
    generate_pdf_report
)

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Логування
logging.basicConfig(level=logging.INFO)

# Авторизація
ADMIN_ID = 6929149032
ALLOWED_USERS = {ADMIN_ID}
DENY_MSG = (
    "❌ You do not have access to this bot.\n\n"
    "If you would like to use it, please send your request "
    "to: mchprojects1@gmail.com"
)

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

def format_user(u) -> str:
    return f"ID={u.id}, Username={u.username}, Name={u.full_name}"

async def notify_admin_about_unauthorized(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg = (
        "🚨 *Unauthorized access attempt detected*\n"
        f"- User: `{format_user(user)}`\n"
        f"- Chat ID: `{chat.id if chat else 'n/a'}`\n"
        f"- Message: `{update.message.text if update.message else 'n/a'}`"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")

# Меню
markup = ReplyKeyboardMarkup(
    [["📄 CV analysis", "🎯 CV and job match analysis"], ["🧠 HR Expert Advice", "💌 Generate Cover Letter"]],
    resize_keyboard=True
)

user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return
    await update.message.reply_text("Hi! Please choose what you’d like to do:", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return
    text = update.message.text
    user_state[user_id] = {}
    if text == "📄 CV analysis":
        user_state[user_id]["mode"] = "resume"
        await update.message.reply_text("Please upload your resume (PDF, DOCX, or TXT).", reply_markup=markup)
    elif text == "🎯 CV and job match analysis":
        user_state[user_id]["mode"] = "vacancy"
        await update.message.reply_text("Upload the job vacancy first, then your CV.", reply_markup=markup)
    elif text == "🧠 HR Expert Advice":
        user_state[user_id]["mode"] = "consult"
        await update.message.reply_text("Upload your CV for HR feedback.", reply_markup=markup)
    elif text == "💌 Generate Cover Letter":
        user_state[user_id]["mode"] = "cover"
        await update.message.reply_text("Upload the job vacancy first, then your CV.", reply_markup=markup)
    else:
        await update.message.reply_text("Please choose an option from the menu ⬇️", reply_markup=markup)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return

    document: Document = update.message.document
    if not document:
        await update.message.reply_text("⚠️ File not received.")
        return

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        file_path = tf.name
        await document.get_file().download_to_drive(file_path)

    await process_input(update, context, file_path)

async def process_input(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    user_id = update.effective_user.id
    mode = user_state.get(user_id, {}).get("mode")
    if not mode:
        await update.message.reply_text("Please select a mode first.", reply_markup=markup)
        return

    try:
        await update.message.reply_text("⌛ Analyzing... Please wait 10–15 seconds.")

        if mode == "resume":
            result = await analyze_resume(file_path)
        elif mode == "consult":
            resume_text = extract_text_from_file(file_path)
            result = await give_hr_feedback(resume_text)
        elif mode == "vacancy":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Thanks! Now send your CV.")
                return
            vacancy_text = extract_text_from_file(user_state[user_id].pop("vacancy"))
            resume_text = extract_text_from_file(file_path)
            result = await analyze_for_vacancy(vacancy_text, resume_text)
        elif mode == "cover":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Thanks! Now send your CV.")
                return
            vacancy_text = extract_text_from_file(user_state[user_id].pop("vacancy"))
            resume_text = extract_text_from_file(file_path)
            result = await generate_cover_letter(vacancy_text, resume_text)
        else:
            await update.message.reply_text("❌ Unknown mode.", reply_markup=markup)
            return

        # Генерація та надсилання PDF
        pdf_path = f"CVise_Report_{user_id}.pdf"
        generate_pdf_report(result, pdf_path)
        await update.message.reply_document(document=open(pdf_path, "rb"), filename="CVise_Report.pdf", reply_markup=markup)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=markup)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    file_filter = filters.Document.ALL

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(file_filter, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
