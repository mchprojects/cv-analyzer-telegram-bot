import os
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from analyzer import (
    extract_text_from_file,
    analyze_resume,
    analyze_for_vacancy,
    give_hr_feedback,
    generate_cover_letter,
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

user_state = {}

ADMIN_ID = 6929149032
ALLOWED_USERS = {ADMIN_ID}
DENY_MSG = (
    "❌ You do not have access to this bot.\n\n"
    "If you would like to use it, please send your request"
    "to: mchprojects1@gmail.com"
)

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

def format_user(u) -> str:
    return f"ID={u.id}, Username={u.username}, Name={u.full_name}"

async def notify_admin_about_unauthorized(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    try:
        msg = (
            "🚨 *Unauthorized access attempt detected*\n"
            f"- User: `{format_user(user)}`\n"
            f"- Chat ID: `{chat.id if chat else 'n/a'}`\n"
            f"- Message: `{update.message.text if update.message else 'n/a'}`"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Failed to notify admin about unauthorized access: {e}")

markup = ReplyKeyboardMarkup(
    [["📄 CV analysis", "🎯 CV and job match analysis"], ["🧠 HR Expert Advice", "💌 Generate Cover Letter"]],
    resize_keyboard=True
)

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

    if text == "📄 CV analysis":
        user_state[user_id] = {"mode": "resume"}
        await update.message.reply_text("Please upload your resume in PDF, DOCX or text format", reply_markup=markup)
    elif text == "🎯 CV and job match analysis":
        user_state[user_id] = {"mode": "vacancy"}
        await update.message.reply_text("Please send the job vacancy (as a PDF, DOCX or text), and then provide your CV", reply_markup=markup)
    elif text == "🧠 HR Expert Advice":
        user_state[user_id] = {"mode": "consult"}
        await update.message.reply_text("Please send your CV for an HR consultation", reply_markup=markup)
    elif text == "💌 Generate Cover Letter":
        user_state[user_id] = {"mode": "cover"}
        await update.message.reply_text("Please send the job vacancy (as a PDF, DOCX or text), and then provide your CV", reply_markup=markup)
    else:
        await update.message.reply_text("Please select a menu option 👇", reply_markup=markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return

    text = update.message.text
    file_path = f"input_{update.message.message_id}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    await process_input(update, context, file_path)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return

    document = update.message.document
    if not document:
        await update.message.reply_text("Please upload your resume in PDF, DOCX or text format")
        return

    file = await context.bot.get_file(document.file_id)
    file_path = f"{document.file_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    await process_input(update, context, file_path)

async def process_input(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return

    mode = user_state.get(user_id, {}).get("mode")

    if not mode:
        await update.message.reply_text("Select an option from the menu 👇", reply_markup=markup)
        return

    try:
        await update.message.reply_text("⌛ Processing your request... This may take 10–15 seconds")

        if mode == "resume":
            result_text, pdf_path = await analyze_resume(file_path)

        elif mode == "vacancy":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Thank you! Please send your CV now")
                return
            else:
                resume_path = file_path
                vacancy_path = user_state[user_id]["vacancy"]
                vacancy_text = extract_text_from_file(vacancy_path)
                result_text, pdf_path = await analyze_for_vacancy(resume_path, vacancy_text)
                del user_state[user_id]["vacancy"]

        elif mode == "consult":
            result_text, pdf_path = await give_hr_feedback(file_path)

        elif mode == "cover":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Thank you! Please send your CV now")
                return
            else:
                resume_path = file_path
                vacancy_path = user_state[user_id]["vacancy"]
                vacancy_text = extract_text_from_file(vacancy_path)
                resume_text = extract_text_from_file(resume_path)
                result_text, pdf_path = await generate_cover_letter(vacancy_text, resume_text)
                del user_state[user_id]["vacancy"]

        else:
            result_text = "❌ Unknown mode. Select an option from the menu 👇"
            pdf_path = None

        user_state[user_id]["last_pdf"] = pdf_path

        for chunk in split_text(result_text):
            await update.message.reply_text(chunk, reply_markup=markup)

        if pdf_path:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Download PDF version", callback_data="send_pdf")]
            ])
            await update.message.reply_text("Would you like to save the result as a PDF?", reply_markup=keyboard)

    except Exception as e:
        await update.message.reply_text(f"Oops—something went wrong. Please try again later: {e}", reply_markup=markup)

def split_text(text, max_length=4000):
    lines = text.split('\n')
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            chunks.append(current)
            current = line
        else:
            current += "\n" + line
    if current:
        chunks.append(current)
    return chunks

async def handle_pdf_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pdf_path = user_state.get(user_id, {}).get("last_pdf")
    if pdf_path and os.path.exists(pdf_path):
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(pdf_path, "rb"))
    else:
        await query.edit_message_text("❌ PDF not found or expired.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    doc_filter = (
        filters.Document.MimeType("application/pdf") |
        filters.Document.MimeType("application/vnd.openxmlformats-officedocument.wordprocessingml.document") |
        filters.Document.FileExtension("txt")
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(doc_filter, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_pdf_request, pattern="send_pdf"))

    app.run_polling()

if __name__ == "__main__":
    main()
