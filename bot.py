import os
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from analyzer import (
    extract_text_from_file,
    analyze_resume,
    analyze_for_vacancy,
    give_hr_feedback,
    generate_cover_letter,
    step_by_step_review,
)

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

user_state = {}
user_results = {}

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
        logging.warning(f"🚨 Unauthorized access attempt! {format_user(user)}")
    except Exception as e:
        logging.error(f"Failed to notify admin about unauthorized access: {e}")

markup = ReplyKeyboardMarkup(
    [["📄 CV analysis", "🌟 Step-by-step CV review"],
     ["🎯 CV and job match analysis", "🧠 HR Expert Advice"],
     ["💌 Generate Cover Letter"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await notify_admin_about_unauthorized(update, context)
        await update.message.reply_text(DENY_MSG)
        return
    await update.message.reply_text("Select an option from the menu 👇", reply_markup=markup)

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
        await update.message.reply_text("Please send the job vacancy (PDF, DOCX or text), and then send your CV")
    elif text == "🧠 HR Expert Advice":
        user_state[user_id] = {"mode": "consult"}
        await update.message.reply_text("Please send your CV for an HR consultation")
    elif text == "💌 Generate Cover Letter":
        user_state[user_id] = {"mode": "cover"}
        await update.message.reply_text("Please send the job vacancy (PDF, DOCX or text), and then send your CV")
    elif text == "🌟 Step-by-step CV review":
        user_state[user_id] = {"mode": "step"}
        await update.message.reply_text("Please upload your CV to start the step-by-step review")
    else:
        await update.message.reply_text("Please select a menu option 👇", reply_markup=markup)

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
    mode = user_state.get(user_id, {}).get("mode")
    if not mode:
        await update.message.reply_text("Select an option from the menu 👇", reply_markup=markup)
        return

    try:
        await update.message.reply_text("⌛ Processing your request... This may take 10–15 seconds")
        if mode == "resume":
            text_result, pdf_path = await analyze_resume(file_path)
        elif mode == "vacancy":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Thank you! Please send your CV now")
                return
            else:
                resume_path = file_path
                vacancy_path = user_state[user_id].pop("vacancy")
                text_result, pdf_path = await analyze_for_vacancy(resume_path, extract_text_from_file(vacancy_path))
        elif mode == "consult":
            text_result, pdf_path = await give_hr_feedback(file_path)
        elif mode == "cover":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Thank you! Please send your CV now")
                return
            else:
                resume_path = file_path
                vacancy_path = user_state[user_id].pop("vacancy")
                text_result, pdf_path = await generate_cover_letter(extract_text_from_file(vacancy_path), extract_text_from_file(resume_path))
        elif mode == "step":
            text_result, pdf_path = await step_by_step_review(file_path)
        else:
            text_result, pdf_path = ("❌ Unknown mode. Select an option from the menu 👇", None)

        for chunk in split_text(text_result):
            await update.message.reply_text(chunk, reply_markup=markup)

        if pdf_path:
            user_results[user_id] = pdf_path
            keyboard = InlineKeyboardMarkup.from_button(
                InlineKeyboardButton("💾 Download PDF version", callback_data="get_pdf")
            )
            await update.message.reply_text("You can download the result as PDF:", reply_markup=keyboard)

    except Exception as e:
        await update.message.reply_text(f"Oops—something went wrong. Please try again later: {e}", reply_markup=markup)

async def handle_pdf_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    pdf_path = user_results.get(user_id)
    if pdf_path and os.path.exists(pdf_path):
        await context.bot.send_document(chat_id=user_id, document=open(pdf_path, "rb"))
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ PDF file not found. Please try again.")

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

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    doc_filter = (
        filters.Document.MimeType("application/pdf") |
        filters.Document.MimeType("application/vnd.openxmlformats-officedocument.wordprocessingml.document") |
        filters.Document.FileExtension("txt")
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_pdf_request, pattern="get_pdf"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(doc_filter, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
