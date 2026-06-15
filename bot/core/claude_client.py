import os
import json
import requests

OLLAMA_URL = 'https://ollama.com/v1/chat/completions'
OLLAMA_MODEL = 'ministral-3:14b'   # генерация ответов
ROUTER_MODEL = 'gemma3:27b'        # роутинг вопросов

# Категории с агрегаторами — только они участвуют в роутинге
ROUTABLE_CATEGORIES = [
    'zadanie_na_kmd',
    'dop_kmd',
    'kartochka_vitrazha_po_km',
    'zns_po_kmd',
]

_ENTITIES_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'entities.json')
)

SYSTEM_PROMPT = """Ты — AI-помощник строительной компании, занимающейся остеклением фасадов зданий.
Отвечаешь на вопросы по данным из системы ELMA365.

## Процесс работы
РП (руководитель проекта) создаёт Задание на КМД по объекту — выбирает корпус, секции и витражи.
Конструктор проектирует КМД. После готовности РП создаёт ЗНС (заявки в снабжение) — отдельную
на каждый тип заполнения (стекло 5мм, стекло 6мм закалка, СМЛ, стеклопакет, ФЦП и т.д.).
Снабжение размещает заказ у поставщика, материал готовится и отгружается.

## Карточки витражей — центральная единица учёта
Каждый витраж имеет карточку (объект / корпус / секция / номер витража / площадь /
разбивка по типам заполнения в м²).
Когда спрашивают про объект, корпус, секцию или конкретный витраж —
ищи через карточки витражей, затем через них смотри задания КМД и ЗНС.

## Основные vs дополнительные задания КМД
- Основное задание: поле dop_zakaz_kmd_ref пустое
- Дополнительное (ДОП): поле dop_zakaz_kmd_ref заполнено
Если в вопросе нет слов «доп», «допы», «дополнительные» — показывай только основные.
Если есть — только дополнительные.

## Статусы Задания на КМД (__status.status)
- 1 или 2 → В работе у конструктора. Плановая дата готовности: rop_date_original
- 5 → Ожидание запуска снабжения (КМД готово, ЗНС ещё не созданы)
- 6 → Снабжение (ЗНС созданы и в работе)
- 3 → Выполнено
- 4 → Прервано
Если статус задания 1 или 2 — про снабжение не говори, его ещё нет.

## Стадии ЗНС — определять по полям, не по статусу ELMA
Определяй стадию по наличию заполненных полей (в порядке приоритета):
1. Есть data_fakt_otgruzki → Отгружено
2. Есть fakt_data_gotovnosti → Готово на складе поставщика
3. Есть data_razmesheniya_u_postavshika или nomer_scheta → Размещено у поставщика
4. Есть supplier_company → Выбран поставщик
5. Есть zns_1s → У МОС (менеджер отдела снабжения)
6. Есть znz_1s, нет zns_1s → У РОС (руководитель отдела снабжения)
7. __status.status = 2, znz_1s пустой → В ПДО
8. __status.status = 1 → Новая (РП создал, не отправил)
Статус id=11 (Подлежит удалению) — не учитывать в подсчётах.
Статус id=8 (Отложена) и id=12 (На корректировке) — упоминать отдельно.

## Ключевые поля
- Плановая дата готовности КМД: rop_date_original
- Факт готовности КМД: fakt_konec_kmd
- Плановая дата готовности ЗНС: plan_data_gotovnosti
  (не обязательно на складе — поставка может быть сразу на объект)
- Факт готовности на складе поставщика: fakt_data_gotovnosti
- Дата отгрузки: data_fakt_otgruzki
- Дата размещения заказа: data_razmesheniya_u_postavshika
- Тип заполнения: vid_zapolneniya
- Номер ЗНЗ в 1С: znz_1s
- Номер ЗНС в 1С: zns_1s

## Правило дедупликации счетов
Один счёт = уникальная комбинация: поставщик + nomer_scheta + summa_scheta.
Один счёт может относиться к нескольким ЗНС — при подсчёте сумм проверяй дубли
и считай такой счёт один раз.

## Правила ответа
- Только факты из переданного контекста, ничего не придумывать
- Если контекст содержит «[Приветствие или мета-фраза]» — отвечай коротко и дружелюбно, правила про данные не применяются
- Если вопрос «Какие КМД / задания в работе» и в контексте есть «Список активных заданий» — перечисли их.
  Если список отсутствует, но есть «В работе по объектам» — ответь перечнем объектов с количеством заданий, это корректный ответ.
- Если данных нет — одна строка: «В данных этого нет.» Точка. Никаких альтернатив.
- ЗАПРЕЩЕНО: разделы «Что можно сделать», «Альтернативный подход», «Рекомендации», советы обратиться к кому-либо или в ELMA вручную
- ЗАПРЕЩЕНО оценивать или предполагать («возможно», «примерно», «по аналогии»)
- Ответ — максимум 8 строк. Больше — только если пользователь явно просит список/детализацию
- НИКОГДА не использовать таблицы (символ | запрещён)
- Каждый пункт с новой строки, через дефис или нумерацию
- Пример формата: "1. Митино К3 с.5 — 3 задания, 890 м², план 15.03.2026"
- Даты — ДД.ММ.ГГГГ, суммы — с разделителем тысяч (1 234 567 ₽)
- Жирный текст (**слово**) и заголовки (###) — можно, таблицы — нельзя"""

MAX_CTX_CHARS = 5000
MAX_HIST_CHARS = 400


def _ollama_chat(messages: list, max_tokens: int = 1024, temperature: float = 0.3, model: str = OLLAMA_MODEL) -> str:
    api_key = os.getenv('OLLAMA_API_KEY')
    if not api_key:
        return 'Ошибка: OLLAMA_API_KEY не задан в .env'
    for attempt in range(2):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={'model': model, 'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature},
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=90,
            )
            resp.raise_for_status()
            msg = resp.json()['choices'][0]['message']
            return (msg.get('content') or '').strip()
        except requests.HTTPError as e:
            return f'Ошибка API ({e.response.status_code}): {e.response.text[:300]}'
        except (requests.ConnectionError, ConnectionResetError):
            if attempt == 0:
                # Обрезаем контекст вдвое и повторяем
                for m in messages:
                    if m.get('role') == 'user' and len(m.get('content', '')) > 2000:
                        m['content'] = m['content'][:2500] + '\n[...данные обрезаны для повтора...]'
                continue
            return 'Ошибка: не удалось подключиться к AI. Попробуй ещё раз.'
        except Exception as e:
            return f'Ошибка соединения: {e}'
    return 'Ошибка: не удалось получить ответ.'


def route_question(question: str) -> list[str]:
    """Определяет нужные категории данных для ответа на вопрос. Возвращает список ID категорий."""
    try:
        with open(_ENTITIES_PATH, 'r', encoding='utf-8') as f:
            all_entities = json.load(f)
    except Exception:
        return ['zadanie_na_kmd']

    entities = [e for e in all_entities if e['id'] in ROUTABLE_CATEGORIES and e.get('routing_hints')]

    catalog = '\n'.join(
        f"- {e['id']}: [{e['routing_hints']}]"
        for e in entities
    )

    prompt = (
        'Choose data categories to answer the question. Return JSON array of IDs only.\n\n'
        f'Categories:\n{catalog}\n\n'
        f'Question: {question}\n\n'
        'Return only JSON array:'
    )

    text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=80, temperature=0, model=ROUTER_MODEL)
    if text and not text.startswith('Ошибка'):
        start, end = text.find('['), text.rfind(']') + 1
        if start >= 0 and end > start:
            try:
                ids = json.loads(text[start:end])
                valid = [i for i in ids if isinstance(i, str) and i in ROUTABLE_CATEGORIES]
                if valid:
                    return valid
            except Exception:
                pass
    return ['zadanie_na_kmd']


_CLARIFICATION_RULES = [
    {
        'trigger':  lambda q: 'заказ' in q and 'задани' not in q,
        'exclude':  ['по кмд', 'в снабжен', 'знс', 'зкс', 'поставк', 'материал', 'озм', 'снабжен'],
        'question': 'Уточни, что именно тебя интересует:',
        'options':  [
            {'label': '📋 Задания конструкторам (КМД)', 'categories': ['zadanie_na_kmd']},
            {'label': '📦 Заказы в снабжение',          'categories': ['order_by_kmd']},
        ],
    },
]


def check_clarification(question: str) -> dict | None:
    """Проверяет неоднозначность вопроса. Возвращает {question, options} или None."""
    q = question.lower()
    for rule in _CLARIFICATION_RULES:
        if rule['trigger'](q) and not any(ex in q for ex in rule['exclude']):
            return {'question': rule['question'], 'options': rule['options']}
    return None


def extract_entities(question: str) -> dict:
    """Извлекает имя сотрудника и/или объект из вопроса."""
    prompt = (
        "Из вопроса пользователя извлеки сущности для поиска в базе данных строительной компании.\n"
        "Правила:\n"
        "- user: фамилия или имя сотрудника (конструктора, исполнителя, автора, РП и т.д.) "
        "в именительном падеже (Иванов, не Иванова/Иванову). null если не упомянут.\n"
        "- object: название или ID объекта СТРОИТЕЛЬСТВА (жилой комплекс, здание, адрес, буквенно-цифровой код). "
        "НЕ является объектом: КМД, доп, задание, тендер, витраж. null если не упомянут.\n"
        "Верни ТОЛЬКО JSON без пояснений:\n"
        '{"user": "...", "object": "..."}\n\n'
        f"Вопрос: {question}"
    )
    text = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=100, temperature=0)
    if text and not text.startswith('Ошибка'):
        start, end = text.find('{'), text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
    return {'user': None, 'object': None}


_FOLLOWUP_STARTS = {'и', 'а', 'ещё', 'тоже', 'также', 'покажи', 'выведи', 'расскажи', 'уточни', 'детализируй'}


def expand_question(question: str, history: list[dict]) -> str:
    """Разворачивает follow-up вопрос в самодостаточный, используя историю диалога."""
    if not history:
        return question
    words = question.lower().split()
    is_short = len(words) <= 7
    starts_followup = bool(words) and words[0] in _FOLLOWUP_STARTS
    if not (is_short or starts_followup):
        return question

    recent = history[-6:]
    history_text = '\n'.join(
        f"{'Пользователь' if m['role'] == 'user' else 'Бот'}: {(m.get('content') or '')[:300]}"
        for m in recent
    )
    prompt = (
        'Диалог о данных строительной компании (остекление фасадов, ELMA365).\n'
        'Последний вопрос неполный — перепиши его в самодостаточный вопрос, сохранив смысл.\n'
        'Верни ТОЛЬКО переформулированный вопрос, без кавычек и пояснений.\n\n'
        f'История:\n{history_text}\n\n'
        f'Исходный вопрос: {question}\n\n'
        'Полный вопрос:'
    )
    result = _ollama_chat([{'role': 'user', 'content': prompt}], max_tokens=120, temperature=0)
    if result and not result.startswith('Ошибка') and len(result) > 3:
        return result.strip().strip('"\'')
    return question


def ask(question: str, context: str, history: list[dict] | None = None) -> str:
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    if history:
        trimmed = []
        for m in (history[:-1] if history[-1]['role'] == 'user' else history):
            content = (m.get('content') or '').strip()
            if not content:
                continue
            if len(content) > MAX_HIST_CHARS:
                content = content[:MAX_HIST_CHARS] + '...'
            trimmed.append({'role': m['role'], 'content': content})
        messages.extend(trimmed)

    ctx_trimmed = context[:MAX_CTX_CHARS]
    if len(context) > MAX_CTX_CHARS:
        ctx_trimmed += '\n[...данные обрезаны...]'
    messages.append({
        'role': 'user',
        'content': f'Данные из ELMA365:\n\n{ctx_trimmed}\n\nВопрос: {question}'
    })

    return _ollama_chat(messages, max_tokens=1024, temperature=0.3)
