import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from analyzer import (
    extract_text_from_file,
    analyze_resume,
    analyze_for_vacancy,
    give_hr_feedback,
    generate_cover_letter,
)

# Логування
logging.basicConfig(level=logging.INFO)

# Токен із .env
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Стан користувача
user_state = {}

# Меню
markup = ReplyKeyboardMarkup(
    [["📄 Розбір резюме", "🎯 Під вакансію"], ["🧠 Консультація", "💌 Супровідний лист"]],
    resize_keyboard=True
)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Обери, що ти хочеш зробити:", reply_markup=markup
    )

# Обробка вибору з меню
async def process_input(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str = None, vacancy_text: str = None):
    mode = user_modes.get(update.effective_user.id)

    # Відправляємо індикатор обробки
    await update.message.reply_text("⌛ Обробляю ваш запит... Це може зайняти 10–15 секунд.")

    if text == "📄 Розбір резюме":
        user_state[user_id] = {"mode": "resume"}
        await update.message.reply_text("Надішли своє резюме у PDF або текстовому форматі.", reply_markup=markup)
    elif text == "🎯 Під вакансію":
        user_state[user_id] = {"mode": "vacancy"}
        await update.message.reply_text("Надішли вакансію (PDF або текстом). Потім надішли своє резюме.", reply_markup=markup)
    elif text == "🧠 Консультація":
        user_state[user_id] = {"mode": "consult"}
        await update.message.reply_text("Надішли своє резюме для HR-консультації.", reply_markup=markup)
    elif text == "💌 Супровідний лист":
        user_state[user_id] = {"mode": "cover"}
        await update.message.reply_text("Надішли вакансію (PDF або текстом). Потім надішли своє резюме.", reply_markup=markup)
    else:
        await update.message.reply_text("Будь ласка, обери опцію з меню 👇", reply_markup=markup)
# Розділяємо великий текст на частини
        for chunk in split_text(result):
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Виникла помилка: {e}")
# Обробка текстових повідомлень як файл-контенту
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    file_path = f"input_{update.message.message_id}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    await process_input(update, context, file_path)

# Обробка PDF або текстових файлів
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        await update.message.reply_text("Будь ласка, надішли файл у форматі PDF або .txt")
        return

    file = await context.bot.get_file(document.file_id)
    file_path = f"{document.file_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    await process_input(update, context, file_path)

# Обробка вхідних даних залежно від режиму
async def process_input(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    user_id = update.effective_user.id
    mode = user_state.get(user_id, {}).get("mode")

    if not mode:
        await update.message.reply_text("Будь ласка, обери опцію з меню 👇", reply_markup=markup)
        return

    try:
        if mode == "resume":
            result = await analyze_resume(file_path)
        elif mode == "vacancy":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Дякую! Тепер надішли своє резюме.")
                return
            else:
                resume_path = file_path
                vacancy_path = user_state[user_id]["vacancy"]
                vacancy_text = extract_text_from_file(vacancy_path)
                resume_text = extract_text_from_file(resume_path)
                result = await analyze_for_vacancy(vacancy_text, resume_text)
                del user_state[user_id]["vacancy"]
        elif mode == "consult":
            resume_text = extract_text_from_file(file_path)
            result = await give_hr_feedback(resume_text)
        elif mode == "cover":
            if "vacancy" not in user_state[user_id]:
                user_state[user_id]["vacancy"] = file_path
                await update.message.reply_text("Дякую! Тепер надішли своє резюме.")
                return
            else:
                resume_path = file_path
                vacancy_path = user_state[user_id]["vacancy"]
                vacancy_text = extract_text_from_file(vacancy_path)
                resume_text = extract_text_from_file(resume_path)
                result = await generate_cover_letter(vacancy_text, resume_text)
                del user_state[user_id]["vacancy"]
        else:
            result = "Невідомий режим. Обери опцію з меню 👇"

        # Надсилання результату по частинах
        for chunk in split_text(result):
            await update.message.reply_text(chunk, reply_markup=markup)

    except Exception as e:
        await update.message.reply_text(f"Виникла помилка: {e}", reply_markup=markup)

# Функція розділення довгого тексту
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

# Запуск бота
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.Document.PDF | filters.Document.TEXT, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
