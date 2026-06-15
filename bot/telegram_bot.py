"""
Telegram-бот ELMA.
Отвечает на вопросы по данным из ELMA365 через Groq AI.
Хранит историю чатов в SQLite.

Запуск: python bot/telegram_bot.py
"""

import os
import sys
import re
import logging
import asyncio
from functools import partial
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.dirname(__file__))
from core.aggregator import build_context_v2 as build_context, search_objects, search_users, search_vitrazhi, get_objects_by_ids, _VITRAZH_CODE_RE
from core import claude_client
from core.claude_client import check_clarification, ROUTABLE_CATEGORIES
from core.history import init_db, save_message, get_context, get_recent

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)



async def _show_object_buttons(update, candidates):
    show = candidates[:4]
    keyboard = [
        [InlineKeyboardButton(display[:60], callback_data=f"obj_{oid}")]
        for oid, display in show
    ]
    if len(candidates) > 4:
        keyboard.append([InlineKeyboardButton("🔍 Уточнить поиск", callback_data="obj_refine")])
    await update.message.reply_text(
        "Найдено несколько объектов, уточни:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _show_user_buttons(update, candidates):
    show = candidates[:4]
    keyboard = [
        [InlineKeyboardButton(display[:60], callback_data=f"usr_{uid}")]
        for uid, display in show
    ]
    if len(candidates) > 4:
        keyboard.append([InlineKeyboardButton("🔍 Уточнить поиск", callback_data="usr_refine")])
    await update.message.reply_text(
        "Найдено несколько сотрудников, уточни:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _safe_send(update, text, retries=3):
    """Отправляет сообщение с повторными попытками при сетевых ошибках."""
    from telegram.error import NetworkError as TGNetworkError
    for attempt in range(retries):
        try:
            await update.message.reply_text(text)
            return
        except TGNetworkError:
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                raise


async def _process_question(update, user, question, object_ids=None, user_id=None,
                            forced_categories=None, vitrazh_code=None):
    """Обрабатывает вопрос и отправляет ответ."""
    await _safe_send(update, "Смотрю данные...")
    try:
        history = get_context(user.id)
        history = [m for m in history if m["content"] != "__clear__"]

        # Разворачиваем короткие follow-up вопросы с опорой на историю
        loop = asyncio.get_event_loop()
        if not object_ids and not user_id and not forced_categories and not vitrazh_code:
            effective_question = await loop.run_in_executor(
                None, partial(claude_client.expand_question, question, history)
            )
            # Если в развёрнутом вопросе появился код объекта — извлекаем его
            if not object_ids and effective_question != question:
                for token in re.findall(r'[а-яёА-ЯЁa-zA-Z]*\d{4,}[а-яёА-ЯЁa-zA-Z]*', effective_question):
                    found = search_objects(token, DATA_DIR)
                    if len(found) == 1:
                        object_ids = [found[0][0]]
                        break
            # Если в развёрнутом вопросе появился код витража — извлекаем его
            if not vitrazh_code and effective_question != question:
                m = _VITRAZH_CODE_RE.search(effective_question)
                if m:
                    vitrazh_code = m.group(0)
        else:
            effective_question = question

        ctx = build_context(effective_question, DATA_DIR, forced_categories=forced_categories,
                            object_ids=object_ids, user_id=user_id, vitrazh_code=vitrazh_code)
        answer = await loop.run_in_executor(
            None, partial(claude_client.ask, effective_question, ctx, history=history)
        )
    except Exception as e:
        answer = f"Ошибка при обработке запроса: {e}"
    save_message(user.id, user.username or '', user.full_name or '', 'assistant', answer)
    await _safe_send(update, answer)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я ELMA-бот. Задавай вопросы по данным — задания КМД, витражи, доп. задания.\n\n"
        "Примеры:\n"
        "• Сколько заданий КМД в работе?\n"
        "• По каким объектам больше всего заданий?\n"
        "• Какие задания КМД по объекту Митино?\n"
        "• Что по конструктору Иванову?\n"
        "• Покажи доп. задания КМД\n\n"
        "/history — последние 10 сообщений\n"
        "/clear — очистить историю разговора"
    )


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    messages = get_recent(user_id, limit=10)
    if not messages:
        await update.message.reply_text("История пуста.")
        return
    lines = []
    for m in messages:
        icon = "👤" if m["role"] == "user" else "🤖"
        text = m["text"][:200] + "..." if len(m["text"]) > 200 else m["text"]
        lines.append(f"{icon} [{m['ts']}]\n{text}")
    await update.message.reply_text("\n\n".join(lines))


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_message(user_id, update.effective_user.username or '',
                 update.effective_user.full_name or '', 'system', '__clear__')
    await update.message.reply_text("Контекст разговора сброшен. Начинаем заново.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    question = update.message.text.strip()
    if not question:
        return

    # Режим уточнения объекта
    if context.user_data.get('awaiting_refinement') == 'obj':
        context.user_data.pop('awaiting_refinement')
        pending = context.user_data.pop('pending_question', question)
        candidates = search_objects(question, DATA_DIR)
        if not candidates:
            await update.message.reply_text("Объект не найден. Попробуй ввести ID или другое название.")
            return
        if len(candidates) == 1:
            save_message(user.id, user.username or '', user.full_name or '', 'user', pending)
            await _process_question(update, user, pending, object_ids=[candidates[0][0]])
        else:
            context.user_data['pending_question'] = pending
            await _show_object_buttons(update, candidates)
        return

    # Режим уточнения пользователя
    if context.user_data.get('awaiting_refinement') == 'usr':
        context.user_data.pop('awaiting_refinement')
        pending = context.user_data.pop('pending_question', question)
        candidates = search_users(question, DATA_DIR)
        if not candidates:
            await update.message.reply_text("Сотрудник не найден.")
            return
        if len(candidates) == 1:
            save_message(user.id, user.username or '', user.full_name or '', 'user', pending)
            await _process_question(update, user, pending, user_id=candidates[0][0])
        else:
            context.user_data['pending_question'] = pending
            await _show_user_buttons(update, candidates)
        return

    save_message(user.id, user.username or '', user.full_name or '', 'user', question)

    # Приветствия и мета-фразы — не тащить данные
    _GREET_KW = {'привет', 'здравствуй', 'здравствуйте', 'добрый', 'добрый день', 'добрый вечер',
                 'спасибо', 'благодарю', 'окей', 'ок', 'понял', 'понятно', 'хорошо', 'ясно', 'пока', 'до свидания'}
    q_clean = question.lower().strip().rstrip('!.,')
    if q_clean in _GREET_KW:
        answer = claude_client.ask(question, '[Приветствие или мета-фраза — данные не нужны]')
        save_message(user.id, user.username or '', user.full_name or '', 'assistant', answer)
        await update.message.reply_text(answer)
        return

    # Проверка неоднозначности — спросить уточнение прежде чем лезть в данные
    clarify = check_clarification(question)
    if clarify:
        context.user_data['pending_question'] = question
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(opt['label'], callback_data=f"cat_{','.join(opt['categories'])}")]
            for opt in clarify['options']
        ])
        await update.message.reply_text(clarify['question'], reply_markup=keyboard)
        return

    # Детекция кода витража (ОФ-17, ВФ-3, НВФ-5 и т.п.) — до поиска объекта
    vitrazh_match = _VITRAZH_CODE_RE.search(question)
    if vitrazh_match:
        candidate = vitrazh_match.group(0)
        kv_hits = search_vitrazhi(candidate, DATA_DIR)
        if kv_hits:
            all_oids = []
            for _, _, oids in kv_hits:
                all_oids.extend(oids)
            unique_oids = list(dict.fromkeys(all_oids))
            if len(unique_oids) == 1:
                await _process_question(update, user, question,
                                        object_ids=unique_oids, vitrazh_code=candidate)
                return
            elif len(unique_oids) > 1:
                context.user_data['pending_question'] = question
                context.user_data['pending_vitrazh_code'] = candidate
                display_list = get_objects_by_ids(unique_oids, DATA_DIR)
                await _show_object_buttons(update, display_list)
                return

    # Локальное извлечение объекта — сначала коды с цифрами (060326ПМ, 160425ВХ и т.п.)
    obj_query = None
    for token in re.findall(r'[а-яёА-ЯЁa-zA-Z]*\d{4,}[а-яёА-ЯЁa-zA-Z]*', question):
        found = search_objects(token, DATA_DIR)
        if len(found) == 1:
            obj_query = token
            break

    # Если кода нет — пробуем слова с заглавной буквы как название объекта
    if not obj_query:
        skip = {'задани', 'витраж', 'конструктор', 'статус', 'выведи', 'покажи', 'сколько',
                'какие', 'какой', 'какая', 'объект', 'работ', 'тендер', 'список', 'последн'}
        for word in re.findall(r'[А-ЯЁ][а-яё]{3,}', question):
            if word.lower() not in skip:
                found = search_objects(word, DATA_DIR)
                if len(found) == 1:
                    obj_query = word
                    break

    if obj_query:
        candidates = search_objects(obj_query, DATA_DIR)
        if len(candidates) == 1:
            await _process_question(update, user, question, object_ids=[candidates[0][0]])
            return
        elif len(candidates) > 1:
            context.user_data['pending_question'] = question
            await _show_object_buttons(update, candidates)
            return

    # Локальное извлечение сотрудника — ищем капитализированные слова в базе пользователей
    user_query = None
    for word in re.findall(r'[А-ЯЁ][а-яё]{3,}', question):
        found = search_users(word, DATA_DIR)
        if len(found) == 1:
            user_query = word
            break

    if user_query:
        candidates = search_users(user_query, DATA_DIR)
        if len(candidates) == 1:
            await _process_question(update, user, question, user_id=candidates[0][0])
            return
        elif 1 < len(candidates) <= 10:
            context.user_data['pending_question'] = question
            await _show_user_buttons(update, candidates)
            return

    await _process_question(update, user, question)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == 'obj_refine':
        await query.edit_message_text("Уточни название или ID объекта:")
        context.user_data['awaiting_refinement'] = 'obj'
        return

    if data == 'usr_refine':
        await query.edit_message_text("Уточни фамилию сотрудника:")
        context.user_data['awaiting_refinement'] = 'usr'
        return

    pending_question = context.user_data.pop('pending_question', '')
    pending_vitrazh_code = context.user_data.pop('pending_vitrazh_code', None)

    if data.startswith('cat_'):
        cats = [c for c in data[4:].split(',') if c in ROUTABLE_CATEGORIES]
        await query.edit_message_text("Смотрю данные...")
        try:
            history = get_context(user.id)
            history = [m for m in history if m["content"] != "__clear__"]
            ctx = build_context(pending_question, DATA_DIR, forced_categories=cats)
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None, partial(claude_client.ask, pending_question, ctx, history=history)
            )
        except Exception as e:
            answer = f"Ошибка: {e}"
        save_message(user.id, user.username or '', user.full_name or '', 'assistant', answer)
        await query.message.reply_text(answer)
        return

    if data.startswith('obj_'):
        obj_id = data[4:]
        await query.edit_message_text("Смотрю данные...")
        # Если выбор объекта был вызван поиском витража — передаём vitrazh_code
        vitrazh_code = pending_vitrazh_code
        if not vitrazh_code:
            m = _VITRAZH_CODE_RE.search(pending_question)
            if m and search_vitrazhi(m.group(0), DATA_DIR):
                vitrazh_code = m.group(0)
        try:
            history = get_context(user.id)
            history = [m for m in history if m["content"] != "__clear__"]
            ctx = build_context(pending_question, DATA_DIR, object_ids=[obj_id], vitrazh_code=vitrazh_code)
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None, partial(claude_client.ask, pending_question, ctx, history=history)
            )
        except Exception as e:
            answer = f"Ошибка: {e}"
        save_message(user.id, user.username or '', user.full_name or '', 'assistant', answer)
        await query.message.reply_text(answer)

    elif data.startswith('usr_'):
        usr_id = data[4:]
        await query.edit_message_text("Смотрю данные...")
        try:
            history = get_context(user.id)
            history = [m for m in history if m["content"] != "__clear__"]
            ctx = build_context(pending_question, DATA_DIR, user_id=usr_id)
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None, partial(claude_client.ask, pending_question, ctx, history=history)
            )
        except Exception as e:
            answer = f"Ошибка: {e}"
        save_message(user.id, user.username or '', user.full_name or '', 'assistant', answer)
        await query.message.reply_text(answer)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: TELEGRAM_BOT_TOKEN не задан в .env")
        sys.exit(1)

    init_db()

    app = (
        ApplicationBuilder()
        .token(token)
        .connect_timeout(30)
        .read_timeout(120)
        .write_timeout(120)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен. Напиши ему в Telegram /start")
    app.run_polling()


if __name__ == "__main__":
    main()
