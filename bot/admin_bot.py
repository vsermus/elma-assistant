"""
Admin-бот — личный бот Виктора.
Присылает отчёты об ошибках раз в час.
Принимает решения по кнопкам: починить / пропустить.

Запуск: python bot/admin_bot.py
"""

import os
import sys
import json
import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.dirname(__file__))
from core.auditor import (
    run as audit_run, DB_PATH, full_analysis,
    get_trends, check_fix_effectiveness, send_recurring_report,
    _ai_recommend, TYPE_LABELS,
)
from core.history import init_db

TODO_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'todo'))

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))


def _conn():
    return sqlite3.connect(DB_PATH)


def _parse_rec(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else [str(v)]
    except Exception:
        return [raw]


def _write_todo(fid: int, ftype: str, question: str, bot_answer: str, category: str, chosen_rec: str) -> str:
    os.makedirs(TODO_DIR, exist_ok=True)
    ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"fix_{ts_str}.md"
    label = TYPE_LABELS.get(ftype, ftype)
    with open(os.path.join(TODO_DIR, fname), 'w', encoding='utf-8') as f:
        f.write(
            f"# Задача: исправить ошибку бота\n\n"
            f"**Тип:** {label}\n"
            f"**Тема:** {category or '—'}\n"
            f"**Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"**ID в базе:** {fid}\n\n"
            f"## Вопрос пользователя\n{question}\n\n"
            f"## Ответ бота\n{bot_answer}\n\n"
            f"## Рекомендация\n{chosen_rec}\n\n"
            f"## Статус\nОткрыта\n"
        )
    with _conn() as c:
        c.execute(
            "UPDATE failures SET status='fixed', fixed_at=? WHERE id=?",
            (datetime.now().isoformat(timespec='seconds'), fid)
        )
    return fname


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, Виктор! Я слежу за ошибками основного бота.\n\n"
        "/audit — запустить проверку сейчас\n"
        "/report — полный анализ диалогов за 7 дней\n"
        "/report 30d — за последние 30 дней\n"
        "/report 2026-05 — за конкретный месяц\n"
        "/failures — все нерешённые проблемы\n"
        "/failures 7d — за последние 7 дней\n"
        "/trends — топ повторяющихся проблем за неделю\n"
        "/stats — статистика"
    )


async def audit_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Проверяю историю чатов...")
    loop = asyncio.get_event_loop()
    problems = await loop.run_in_executor(None, audit_run)
    if not problems:
        await update.message.reply_text("✅ Проблем не найдено за последний час.")
    else:
        await update.message.reply_text(f"Найдено {len(problems)} проблем — отправляю.")


async def show_failures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    period_clause = ""
    period_label = "все открытые"

    if args:
        arg = args[0]
        if arg.endswith('d') and arg[:-1].isdigit():
            days = int(arg[:-1])
            since = (datetime.now() - timedelta(days=days)).isoformat(timespec='seconds')
            period_clause = f" AND ts >= '{since}'"
            period_label = f"за последние {days} дн."
        elif len(arg) == 7 and arg[4] == '-':
            period_clause = f" AND ts LIKE '{arg}%'"
            period_label = f"за {arg}"

    with _conn() as c:
        rows = c.execute(
            f"SELECT id, type, question, bot_answer, ts, recommendation FROM failures "
            f"WHERE status='new'{period_clause} ORDER BY id DESC LIMIT 20"
        ).fetchall()

    if not rows:
        await update.message.reply_text(f"✅ Нерешённых проблем нет ({period_label}).")
        return

    await update.message.reply_text(f"📋 Нерешённые проблемы ({period_label}): {len(rows)}")
    for fid, ftype, question, bot_answer, ts, rec in rows:
        label = TYPE_LABELS.get(ftype, ftype)
        text = f"{label} [{ts[:16]}]\n❓ {question[:200]}\n🤖 {bot_answer[:200]}"
        if rec:
            text += f"\n💡 {rec[:150]}"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Починить", callback_data=f"fix_{fid}"),
            InlineKeyboardButton("❌ Пропустить", callback_data=f"skip_{fid}"),
            InlineKeyboardButton("🚫 Не нужно", callback_data=f"ignore_{fid}"),
        ]])
        await update.message.reply_text(text, reply_markup=keyboard)


async def trends_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loop = asyncio.get_event_loop()
    trends = await loop.run_in_executor(None, get_trends)

    if not trends:
        await update.message.reply_text("За последние 7 дней проблем не зафиксировано.")
        return

    lines = ["📈 <b>Топ проблем за 7 дней:</b>\n"]
    for i, t in enumerate(trends, 1):
        label = TYPE_LABELS.get(t['type'], t['type'])
        lines.append(f"{i}. {label} — {t['category']} ({t['count']} раз)")
    await update.message.reply_text('\n'.join(lines), parse_mode='HTML')


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
        new = c.execute("SELECT COUNT(*) FROM failures WHERE status='new'").fetchone()[0]
        fixed = c.execute("SELECT COUNT(*) FROM failures WHERE status='fixed'").fetchone()[0]
        skipped = c.execute("SELECT COUNT(*) FROM failures WHERE status='skipped'").fetchone()[0]
        ignored = c.execute("SELECT COUNT(*) FROM failures WHERE status='ignored'").fetchone()[0]
        by_type = c.execute(
            "SELECT type, COUNT(*) FROM failures GROUP BY type ORDER BY COUNT(*) DESC"
        ).fetchall()
        top_categories = c.execute(
            "SELECT category, COUNT(*) as cnt FROM failures "
            "WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC LIMIT 5"
        ).fetchall()

    type_lines = '\n'.join(
        f"  {TYPE_LABELS.get(t, t)} — {cnt}" for t, cnt in by_type
    ) if by_type else '  нет данных'
    cat_lines = '\n'.join(f"  {cat} — {cnt}" for cat, cnt in top_categories) if top_categories else '  нет данных'

    await update.message.reply_text(
        f"📊 Статистика проблем:\n"
        f"  Всего найдено: {total}\n"
        f"  Ждут решения: {new}\n"
        f"  Починено: {fixed}\n"
        f"  Пропущено: {skipped}\n"
        f"  Не нужно: {ignored}\n\n"
        f"📌 По типам:\n{type_lines}\n\n"
        f"📌 По темам:\n{cat_lines}"
    )


async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    since = None
    period_label = "за 7 дней"

    if args:
        arg = args[0]
        if arg.endswith('d') and arg[:-1].isdigit():
            days = int(arg[:-1])
            since = (datetime.now() - timedelta(days=days)).isoformat(timespec='seconds')
            period_label = f"за {days} дн."
        elif len(arg) == 7 and arg[4] == '-':
            since = f"{arg}-01T00:00:00"
            period_label = f"за {arg}"
    else:
        since = (datetime.now() - timedelta(days=7)).isoformat(timespec='seconds')

    await update.message.reply_text(f"Анализирую диалоги {period_label}...")

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: full_analysis(since))

    total = data['total']
    if not total:
        await update.message.reply_text(f"Диалогов {period_label} нет.")
        return

    results = data['results']
    scores = [r.get('quality', 3) for r in results]
    avg = sum(scores) / len(scores)
    dist = {i: scores.count(i) for i in range(1, 6)}

    from collections import Counter
    categories = Counter(r.get('category', 'неизвестно') for r in results)
    bad = [r for r in results if r.get('quality', 3) <= 2]

    bars = ''.join(f"\n  {'⭐' * i}({i}) — {dist.get(i, 0)}" for i in range(5, 0, -1))
    text = (
        f"📊 <b>Отчёт по диалогам {period_label}</b>\n"
        f"Всего диалогов: {total}\n"
        f"Средняя оценка: {avg:.1f}/5\n\n"
        f"<b>Распределение оценок:</b>{bars}\n\n"
    )

    if categories:
        top_cats = categories.most_common(5)
        cat_lines = '\n'.join(f"  {cat} — {cnt}" for cat, cnt in top_cats)
        text += f"<b>Темы вопросов:</b>\n{cat_lines}"

    await update.message.reply_text(text, parse_mode='HTML')

    if bad:
        bad_text = f"⚠️ <b>Проблемные ответы ({len(bad)}):</b>\n\n"
        for r in bad[:5]:
            stars = '⭐' * r.get('quality', 1)
            bad_text += f"{stars} [{r.get('category', '')}]\n❓ {r['question'][:100]}\n"
            if r.get('fix'):
                bad_text += f"🔧 {r['fix'][:150]}\n"
            bad_text += "\n"
        await update.message.reply_text(bad_text, parse_mode='HTML')

    fixes = [r['fix'] for r in results if r.get('fix')]
    if fixes:
        unique_fixes = list(dict.fromkeys(fixes))[:6]
        fixes_text = "💡 <b>Рекомендации:</b>\n" + '\n'.join(f"• {f[:150]}" for f in unique_fixes)
        await update.message.reply_text(fixes_text, parse_mode='HTML')


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_', 2)
    action = parts[0]
    fid = int(parts[1])

    with _conn() as c:
        row = c.execute(
            "SELECT type, question, bot_answer, category, recommendation FROM failures WHERE id=?", (fid,)
        ).fetchone()

    if not row:
        await query.edit_message_text("Проблема уже обработана.")
        return

    ftype, question, bot_answer, category, recommendation = row
    label = TYPE_LABELS.get(ftype, ftype)

    if action == 'skip':
        with _conn() as c:
            c.execute("UPDATE failures SET status='skipped' WHERE id=?", (fid,))
        await query.edit_message_text(f"❌ Пропущено:\n{question[:100]}")

    elif action == 'ignore':
        with _conn() as c:
            c.execute("UPDATE failures SET status='ignored' WHERE id=?", (fid,))
        await query.edit_message_text(f"🚫 Отмечено как «не нужно»:\n{question[:100]}")

    elif action == 'fix':
        variants = _parse_rec(recommendation)
        if not variants:
            await query.edit_message_text("⏳ Генерирую варианты решения...")
            loop = asyncio.get_event_loop()
            variants = await loop.run_in_executor(
                None, lambda: _ai_recommend(question, bot_answer, ftype, category or '')
            )
            with _conn() as c:
                c.execute(
                    "UPDATE failures SET recommendation=? WHERE id=?",
                    (json.dumps(variants, ensure_ascii=False), fid)
                )

        text = (
            f"💡 <b>Варианты решения</b>\n"
            f"{label} — {category or ''}\n"
            f"❓ {question[:150]}\n\n"
        )
        for i, v in enumerate(variants, 1):
            text += f"<b>{i}.</b> {v}\n\n"

        buttons = [
            InlineKeyboardButton(f"Вариант {i + 1}", callback_data=f"pick_{fid}_{i}")
            for i in range(len(variants))
        ]
        keyboard = InlineKeyboardMarkup([
            buttons,
            [InlineKeyboardButton("✏️ Своя редакция", callback_data=f"edit_{fid}")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')

    elif action == 'pick':
        idx = int(parts[2]) if len(parts) > 2 else 0
        variants = _parse_rec(recommendation)
        chosen = variants[idx] if idx < len(variants) else (variants[0] if variants else '—')
        loop = asyncio.get_event_loop()
        fname = await loop.run_in_executor(
            None, lambda: _write_todo(fid, ftype, question, bot_answer, category or '', chosen)
        )
        await query.edit_message_text(
            f"✅ Задача записана: todo/{fname}\n\n"
            f"{label} — {category or ''}\n"
            f"❓ <b>Вопрос:</b> {question[:150]}\n\n"
            f"💡 <b>Рекомендация:</b>\n{chosen}\n\n"
            "Открой в Claude Code и скажи: «почини задачи из todo/»",
            parse_mode='HTML'
        )

    elif action == 'edit':
        context.user_data['awaiting_edit'] = fid
        await query.edit_message_text(
            f"✏️ Введи свою рекомендацию для проблемы #{fid}:\n\n"
            f"{label} — {category or ''}\n"
            f"❓ {question[:200]}"
        )


async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fid = context.user_data.pop('awaiting_edit', None)
    if fid is None:
        return
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return

    chosen = update.message.text.strip()
    with _conn() as c:
        row = c.execute(
            "SELECT type, question, bot_answer, category FROM failures WHERE id=?", (fid,)
        ).fetchone()

    if not row:
        await update.message.reply_text("Проблема не найдена.")
        return

    ftype, question, bot_answer, category = row
    label = TYPE_LABELS.get(ftype, ftype)
    loop = asyncio.get_event_loop()
    fname = await loop.run_in_executor(
        None, lambda: _write_todo(fid, ftype, question, bot_answer, category or '', chosen)
    )
    await update.message.reply_text(
        f"✅ Задача записана: todo/{fname}\n\n"
        f"{label} — {category or ''}\n"
        f"❓ <b>Вопрос:</b> {question[:150]}\n\n"
        f"💡 <b>Рекомендация:</b>\n{chosen}\n\n"
        "Открой в Claude Code и скажи: «почини задачи из todo/»",
        parse_mode='HTML'
    )


async def hourly_audit(context: ContextTypes.DEFAULT_TYPE):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, audit_run)
    recurring = await loop.run_in_executor(None, check_fix_effectiveness)
    if recurring:
        await loop.run_in_executor(None, lambda: send_recurring_report(recurring))


def main():
    token = os.getenv('ADMIN_BOT_TOKEN')
    if not token:
        print("Ошибка: ADMIN_BOT_TOKEN не задан в .env")
        sys.exit(1)

    init_db()
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("audit", audit_now))
    app.add_handler(CommandHandler("failures", show_failures))
    app.add_handler(CommandHandler("trends", trends_cmd))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("report", report_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_input))

    app.job_queue.run_repeating(hourly_audit, interval=3600, first=60)

    print("Admin-бот запущен. Аудит каждый час.")
    app.run_polling()


if __name__ == "__main__":
    main()
