"""
Аудитор чатов — раз в час ищет проблемы и шлёт отчёт в Telegram.

Типы проблем:
  routing_error  — данные есть, роутер выбрал не ту категорию
  missing_data   — данных нет ни в одной категории
  answer_quality — данные были, ответ плохой
"""

import os
import sqlite3
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'chat_history.db'))
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))

OLLAMA_MODEL = 'gemma3:27b'
OLLAMA_URL = 'https://ollama.com/v1/chat/completions'

PROBLEM_TYPES = ('routing_error', 'missing_data', 'answer_quality')

TYPE_LABELS = {
    'routing_error':  '🔀 Роутинг',
    'missing_data':   '📭 Нет данных',
    'answer_quality': '📉 Плохой ответ',
}


def _conn():
    return sqlite3.connect(DB_PATH)


def _ollama_chat(messages: list, max_tokens: int = 300, temperature: float = 0) -> str | None:
    api_key = os.getenv('OLLAMA_API_KEY')
    if not api_key:
        return None
    try:
        payload = json.dumps({
            'model': OLLAMA_MODEL,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }).encode('utf-8')
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            return resp['choices'][0]['message']['content'].strip()
    except Exception:
        return None


def _ai_classify_batch(pairs: list) -> list:
    """Классифицирует пакет диалогов. Возвращает список {type, category}."""
    dialogs = ''
    for i, p in enumerate(pairs, 1):
        dialogs += f"[{i}] Вопрос: {p['question'][:200]}\nОтвет бота: {p['answer'][:300]}\n\n"

    prompt = (
        f"Проанализируй {len(pairs)} диалогов. Для каждого — есть ли проблема в ответе бота?\n\n"
        "Типы проблем:\n"
        "- routing_error: бот ответил данными не из той области (спросили про витражи — ответил про тендеры)\n"
        "- missing_data: данных по этой теме в системе нет вообще\n"
        "- answer_quality: данные были, но ответ неполный, непонятный или неточный\n\n"
        f"{dialogs}"
        f"Верни JSON-массив из ровно {len(pairs)} объектов:\n"
        "[{\"type\": \"routing_error\"/\"missing_data\"/\"answer_quality\"/null, \"category\": \"тема 1-2 словами\"}, ...]\n"
        "null — если ответ нормальный. Только JSON, без пояснений."
    )
    text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=len(pairs) * 60)
    if text:
        start, end = text.find('['), text.rfind(']') + 1
        if start >= 0 and end > start:
            try:
                items = json.loads(text[start:end])
                results = []
                for item in items[:len(pairs)]:
                    ptype = item.get('type')
                    results.append({
                        'type': ptype if ptype in PROBLEM_TYPES else None,
                        'category': item.get('category', 'неизвестно'),
                    })
                while len(results) < len(pairs):
                    results.append({'type': None, 'category': 'неизвестно'})
                return results
            except Exception:
                pass
    return [{'type': None, 'category': 'неизвестно'} for _ in pairs]


def _ai_recommend(question: str, bot_answer: str, problem_type: str, category: str) -> list[str]:
    """Генерирует 2-3 варианта рекомендаций под тип проблемы."""
    if problem_type == 'routing_error':
        prompt = (
            f"Бот ответил не теми данными на вопрос про «{category}».\n"
            f"Вопрос: {question[:200]}\n"
            f"Ответ бота: {bot_answer[:200]}\n\n"
            "Дай 2-3 конкретных варианта исправления: какую категорию или routing_hint добавить/изменить. "
            "Верни JSON-массив строк: [\"вариант1\", \"вариант2\"]. Только JSON, без пояснений."
        )
    elif problem_type == 'missing_data':
        prompt = (
            f"Бот не смог ответить на вопрос про «{category}» — данных нет в системе.\n"
            f"Вопрос: {question[:200]}\n\n"
            "Дай 2-3 конкретных варианта: какой запрос к ELMA добавить или какого поля не хватает. "
            "Верни JSON-массив строк: [\"вариант1\", \"вариант2\"]. Только JSON, без пояснений."
        )
    else:
        prompt = (
            f"Данные были, но ответ бота на вопрос про «{category}» получился плохим.\n"
            f"Вопрос: {question[:200]}\n"
            f"Ответ бота: {bot_answer[:200]}\n\n"
            "Дай 2-3 конкретных варианта: что именно улучшить в агрегаторе или промпте. "
            "Верни JSON-массив строк: [\"вариант1\", \"вариант2\"]. Только JSON, без пояснений."
        )
    text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=200, temperature=0.3)
    if text:
        start, end = text.find('['), text.rfind(']') + 1
        if start >= 0 and end > start:
            try:
                items = json.loads(text[start:end])
                variants = [str(v).strip() for v in items if v][:3]
                if variants:
                    return variants
            except Exception:
                pass
        return [text.strip()]
    return ['— не удалось получить рекомендацию']


def _ai_is_duplicate(question: str, known: list[str]) -> bool:
    """Проверяет через AI — похож ли вопрос на уже известные проблемы."""
    if not known:
        return False
    sample = known[-10:]
    prompt = (
        f"Новый вопрос: «{question[:200]}»\n\n"
        "Похожие проблемы уже зафиксированы:\n" +
        '\n'.join(f"- {q[:150]}" for q in sample) +
        "\n\nЯвляется ли новый вопрос по сути тем же самым? Ответь только: yes или no."
    )
    text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=5)
    return bool(text and 'yes' in text.lower())


def _get_last_audit_ts() -> str:
    with _conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key='last_audit_ts'").fetchone()
    if row:
        return row[0]
    return (datetime.now() - timedelta(hours=24)).isoformat(timespec='seconds')


def _set_last_audit_ts(ts: str):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_audit_ts', ?)", (ts,)
        )


def _known_questions(ptype: str) -> list[str]:
    with _conn() as c:
        rows = c.execute(
            "SELECT question FROM failures WHERE type=? AND status IN ('new','fixed')", (ptype,)
        ).fetchall()
    return [r[0] for r in rows]


def scan_recent(since: str | None = None) -> list[dict]:
    """Сканирует сообщения через AI-классификацию. По умолчанию — с последнего аудита."""
    if since is None:
        since = _get_last_audit_ts()

    with _conn() as c:
        rows = c.execute(
            "SELECT id, user_id, role, text, ts FROM messages WHERE ts >= ? ORDER BY id",
            (since,)
        ).fetchall()

    if not rows:
        return []

    user_rows = defaultdict(list)
    last_uid = None
    for row in rows:
        _, uid, role, _, _ = row
        if role == 'user':
            last_uid = uid
            user_rows[uid].append(row)
        elif role == 'assistant' and last_uid is not None:
            user_rows[last_uid].append(row)

    pairs = []
    for uid, urows in user_rows.items():
        for i, (mid, _, role, text, ts) in enumerate(urows):
            if role == 'assistant':
                question = ''
                for j in range(i - 1, max(i - 5, -1), -1):
                    if urows[j][2] == 'user':
                        question = urows[j][3]
                        break
                if question:
                    pairs.append({'question': question, 'answer': text, 'ts': ts, 'user_id': uid})

    if not pairs:
        return []

    problems = []
    known_by_type = {}
    batch_size = 5

    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i + batch_size]
        classifications = _ai_classify_batch(batch)

        for pair, cls in zip(batch, classifications):
            ptype = cls.get('type')
            if not ptype:
                continue

            if ptype not in known_by_type:
                known_by_type[ptype] = _known_questions(ptype)

            if _ai_is_duplicate(pair['question'], known_by_type[ptype]):
                continue

            recommendation = _ai_recommend(
                pair['question'], pair['answer'], ptype, cls.get('category', '')
            )

            problems.append({
                'type': ptype,
                'question': pair['question'],
                'bot_answer': pair['answer'][:500],
                'user_id': pair['user_id'],
                'ts': pair['ts'],
                'category': cls.get('category'),
                'recommendation': recommendation,
            })
            known_by_type[ptype].append(pair['question'])

    return problems


def save_failures(problems: list[dict]):
    """Сохраняет проблемы в БД, добавляет id в каждый словарь."""
    with _conn() as conn:
        cur = conn.cursor()
        for p in problems:
            rec = p.get('recommendation', [])
            rec_json = json.dumps(rec, ensure_ascii=False) if isinstance(rec, list) else rec
            cur.execute(
                "INSERT INTO failures (type, question, bot_answer, user_id, ts, category, recommendation) "
                "VALUES (?,?,?,?,?,?,?)",
                (p['type'], p['question'], p['bot_answer'], p.get('user_id'),
                 p['ts'], p.get('category'), rec_json)
            )
            p['id'] = cur.lastrowid


def get_trends(days: int = 7) -> list[dict]:
    """Топ повторяющихся проблем за последние N дней."""
    since = (datetime.now() - timedelta(days=days)).isoformat(timespec='seconds')
    with _conn() as c:
        rows = c.execute(
            """
            SELECT type, category, COUNT(*) as cnt
            FROM failures
            WHERE ts >= ? AND status != 'ignored'
            GROUP BY type, category
            ORDER BY cnt DESC
            LIMIT 5
            """,
            (since,)
        ).fetchall()
    return [{'type': r[0], 'category': r[1], 'count': r[2]} for r in rows]


def check_fix_effectiveness() -> list[dict]:
    """Проверяет фиксы ~7 дней назад — всё ещё приходят похожие вопросы?"""
    week_ago = (datetime.now() - timedelta(days=7)).isoformat(timespec='seconds')
    eight_days_ago = (datetime.now() - timedelta(days=8)).isoformat(timespec='seconds')

    with _conn() as c:
        fixed = c.execute(
            "SELECT id, question, type, category FROM failures "
            "WHERE status='fixed' AND fixed_at >= ? AND fixed_at < ?",
            (eight_days_ago, week_ago)
        ).fetchall()

    if not fixed:
        return []

    with _conn() as c:
        recent = c.execute(
            "SELECT text FROM messages WHERE role='user' AND ts >= ?", (week_ago,)
        ).fetchall()
    recent_texts = [r[0] for r in recent]

    if not recent_texts:
        return []

    recurring = []
    for fid, question, ftype, category in fixed:
        sample = recent_texts[:20]
        prompt = (
            f"Исходная проблема: «{question[:200]}» (тема: {category})\n\n"
            "Недавние вопросы пользователей:\n" +
            '\n'.join(f"- {q[:150]}" for q in sample) +
            "\n\nЕсть ли среди недавних вопросов похожие по теме? Ответь только: yes или no."
        )
        text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=5)
        if text and 'yes' in text.lower():
            recurring.append({'id': fid, 'question': question, 'type': ftype, 'category': category})

    return recurring


def _send_telegram(token: str, chat_id: str, text: str, reply_markup: dict | None = None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def send_report(problems: list[dict]):
    token = os.getenv('ADMIN_BOT_TOKEN')
    chat_id = os.getenv('ADMIN_CHAT_ID')
    if not token or not chat_id or not problems:
        return

    header = f"🔍 <b>Аудит — {datetime.now().strftime('%d.%m %H:%M')}</b>\nНайдено проблем: {len(problems)}\n\n"

    for i, p in enumerate(problems, 1):
        label = TYPE_LABELS.get(p['type'], p['type'])
        raw_rec = p.get('recommendation', [])
        if isinstance(raw_rec, list):
            variants = raw_rec
        else:
            try:
                variants = json.loads(raw_rec)
            except Exception:
                variants = [raw_rec] if raw_rec else []
        rec_preview = variants[0][:200] if variants else ''
        msg = (
            f"{i}. {label} — {p.get('category', '')}\n"
            f"❓ <b>Вопрос:</b> {p['question'][:150]}\n"
            f"🤖 <b>Ответ:</b> {p['bot_answer'][:200]}\n"
        )
        if rec_preview:
            msg += f"💡 <b>Вариант 1:</b> {rec_preview}\n"

        db_id = p.get('id', i)
        markup = {
            'inline_keyboard': [[
                {'text': '✅ Починить', 'callback_data': f"fix_{db_id}"},
                {'text': '❌ Пропустить', 'callback_data': f"skip_{db_id}"},
                {'text': '🚫 Не нужно', 'callback_data': f"ignore_{db_id}"},
            ]]
        }
        _send_telegram(token, chat_id, header + msg if i == 1 else msg, markup)


def send_recurring_report(recurring: list[dict]):
    """Шлёт напоминание о нефиксированных проблемах."""
    token = os.getenv('ADMIN_BOT_TOKEN')
    chat_id = os.getenv('ADMIN_CHAT_ID')
    if not token or not chat_id or not recurring:
        return

    text = "⚠️ <b>Проблемы всё ещё повторяются (прошло 7 дней):</b>\n\n"
    for r in recurring:
        label = TYPE_LABELS.get(r['type'], r['type'])
        text += f"• {label} — {r['category']}\n  {r['question'][:120]}\n\n"
    _send_telegram(token, chat_id, text)


def run():
    started_at = datetime.now().isoformat(timespec='seconds')
    problems = scan_recent()
    if problems:
        save_failures(problems)
        send_report(problems)
    _set_last_audit_ts(started_at)
    return problems


# --- Оставлено для /report в admin_bot ---

def _ollama_analyze_batch(pairs: list) -> list:
    dialogs = ''
    for i, p in enumerate(pairs, 1):
        dialogs += f"[{i}] Вопрос: {p['question'][:200]}\nОтвет бота: {p['answer'][:300]}\n\n"

    prompt = (
        f"Оцени качество ответов бота. Диалогов: {len(pairs)}.\n"
        "Верни JSON-массив:\n"
        "[{\"quality\":1-5,\"issue\":\"проблема или null\",\"fix\":\"что исправить или null\",\"category\":\"тема\"},...]\n\n"
        f"{dialogs}"
        "quality: 5=отличный, 1=не ответил.\n"
        f"Верни ровно {len(pairs)} объекта. Только JSON."
    )
    text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=len(pairs) * 150)
    if text:
        start, end = text.find('['), text.rfind(']') + 1
        if start >= 0 and end > start:
            try:
                items = json.loads(text[start:end])
                results = []
                for j, item in enumerate(items[:len(pairs)]):
                    item['ts'] = pairs[j]['ts']
                    item['question'] = pairs[j]['question'][:150]
                    results.append(item)
                for j in range(len(results), len(pairs)):
                    results.append({'quality': 3, 'issue': None, 'fix': None,
                                    'category': 'неизвестно', 'ts': pairs[j]['ts'],
                                    'question': pairs[j]['question'][:150]})
                return results
            except Exception:
                pass
    return [{'quality': 3, 'issue': None, 'fix': None, 'category': 'неизвестно',
             'ts': p['ts'], 'question': p['question'][:150]} for p in pairs]


def full_analysis(since: str | None = None) -> dict:
    if since is None:
        since = (datetime.now() - timedelta(days=7)).isoformat(timespec='seconds')

    with _conn() as c:
        rows = c.execute(
            "SELECT id, user_id, role, text, ts FROM messages WHERE ts >= ? ORDER BY id",
            (since,)
        ).fetchall()

    if not rows:
        return {'total': 0, 'results': [], 'since': since}

    user_rows = defaultdict(list)
    last_uid = None
    for row in rows:
        _, uid, role, _, _ = row
        if role == 'user':
            last_uid = uid
            user_rows[uid].append(row)
        elif role == 'assistant' and last_uid is not None:
            user_rows[last_uid].append(row)

    pairs = []
    for uid, urows in user_rows.items():
        for i, (mid, _, role, text, ts) in enumerate(urows):
            if role == 'assistant':
                question = ''
                for j in range(i - 1, max(i - 5, -1), -1):
                    if urows[j][2] == 'user':
                        question = urows[j][3]
                        break
                if question:
                    pairs.append({'question': question, 'answer': text, 'ts': ts})

    results = []
    for i in range(0, len(pairs), 5):
        results.extend(_ollama_analyze_batch(pairs[i:i + 5]))

    return {'total': len(pairs), 'results': results, 'since': since}
