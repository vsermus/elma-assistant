import os
import json
import logging
import subprocess
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
GANTT_SCRIPT = os.path.join(ROOT_DIR, "scripts", "process", "vitrage_gantt.py")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation States
SEARCHING, SELECTING_CORPUS = range(2)

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "result" in data:
        res = data["result"]
        if isinstance(res, dict) and "result" in res:
            return res["result"]
        return res
    return data

def get_objects():
    data = load_json("spravochnik_id.json")
    return data if data else []

def get_vitrages():
    data = load_json("kartochka_vitrazha_po_km.json")
    return data if data else []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Здравствуйте! Я помогу вам получить **график КМД по витражам**.\n\n"
        "**Как со мной работать:**\n"
        "1. Напишите название или ID объекта.\n"
        "2. Выберите нужный объект из списка.\n"
        "3. Укажите корпус.\n"
        "4. Получите файл.\n\n"
        "Жду ваших вводных данных!"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(welcome_text, parse_mode="Markdown")
    return SEARCHING

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()
    objects = get_objects()

    matches = []
    for obj in objects:
        iid = (obj.get("itogovyi_id") or "").lower()
        name = (obj.get("kodovoe_nazvanie") or "").lower()

        if query == iid:
            matches.insert(0, obj) # Priority to exact ID match
        elif query in iid or query in name:
            matches.append(obj)

    # Remove duplicates if exact match was found
    seen = set()
    unique_matches = []
    for m in matches:
        if m.get("itogovyi_id") not in seen:
            unique_matches.append(m)
            seen.add(m.get("itogovyi_id"))

    if not unique_matches:
        await update.message.reply_text("К сожалению, объект не найден. Попробуйте ввести ID или другое название.")
        return SEARCHING

    # Limit to 5 + 1
    limit = 5
    display_matches = unique_matches[:limit]

    keyboard = []
    for m in display_matches:
        text = f"{m.get('kodovoe_nazvanie')} ({m.get('itogovyi_id')})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"obj_{m.get('itogovyi_id')}")])

    if len(unique_matches) > limit:
        keyboard.append([InlineKeyboardButton("🔍 Уточнить поиск", callback_data="refine_search")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = "Я нашел следующие объекты. Выберите нужный:" if len(unique_matches) > 1 else "Объект найден:"
    await update.message.reply_text(msg, reply_markup=reply_markup)
    return SEARCHING

async def object_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    obj_id = query.data.replace("obj_", "")
    context.user_data["selected_obj_id"] = obj_id

    # Get available corpuses for this object
    vitrages = get_vitrages()
    corpuses = set()
    for v in vitrages:
        if v.get("itogovyi_id") == obj_id:
            c = v.get("korpus")
            if c: corpuses.add(c)

    sorted_corpuses = sorted(list(corpuses))

    if not sorted_corpuses:
        # Try to find in spravochnik_id if not in vitrages?
        # No, the graph needs vitrage data.
        await query.edit_message_text(f"Для объекта {obj_id} не найдено данных о корпусах в карточках витражей.")
        return SEARCHING

    keyboard = []
    for c in sorted_corpuses:
        keyboard.append([InlineKeyboardButton(c, callback_data=f"corp_{c}")])

    keyboard.append([InlineKeyboardButton("Все корпуса", callback_data="corp_all")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Объект {obj_id} выбран. Теперь выберите корпус:", reply_markup=reply_markup)
    return SELECTING_CORPUS

async def corpus_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    corpus = query.data.replace("corp_", "")
    obj_id = context.user_data.get("selected_obj_id")

    await query.edit_message_text(f"Формирую график для {obj_id}, корпус {corpus}... Пожалуйста, подождите.")

    # Call the generator script
    cmd = [
        "python",
        GANTT_SCRIPT,
        "--object", obj_id,
    ]
    if corpus != "all":
        cmd.extend(["--corpus", corpus])

    try:
        # Run script
        process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if process.returncode != 0:
            raise Exception(process.stderr)

        # The script saves file to reports/grafik_vitrazhey_{obj_id}.xlsx
        file_path = os.path.join(REPORTS_DIR, f"grafik_vitrazhey_{obj_id}.xlsx")

        if os.path.exists(file_path):
            await query.message.reply_document(
                document=open(file_path, "rb"),
                filename=f"grafik_vitrazhey_{obj_id}.xlsx",
                caption=f"✅ Готово! График КМД по витражам для объекта {obj_id}."
            )
        else:
            await query.message.reply_text("Ошибка: Файл не был создан скриптом генерации.")

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await query.message.reply_text(f"Произошла ошибка при генерации файла: {e}")

    return SEARCHING # Return to start state

async def refine_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пожалуйста, уточните название или введите точный ID объекта.")
    return SEARCHING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено. Используйте /start для нового поиска.")
    return ConversationHandler.END

def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search)
        ],
        states={
            SEARCHING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search),
                CallbackQueryHandler(refine_search, pattern="^refine_search$"),
                CallbackQueryHandler(object_selected, pattern="^obj_"),
            ],
            SELECTING_CORPUS: [
                CallbackQueryHandler(corpus_selected, pattern="^corp_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
