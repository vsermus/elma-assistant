---
name: elma-assistant
description: Работа с проектом ELMA Assistant — AI-бот по данным ELMA365. Понимание структуры, запуск ботов, обновление данных, добавление субагентов, проверка ошибок, публикация на GitHub.
license: MIT
compatibility: opencode
metadata:
  workflow: elma
---

## Что это за проект

**ELMA Assistant** — Telegram-бот, который отвечает на вопросы сотрудников по данным из корпоративной системы ELMA365.

Состоит из двух ботов:
- `bot/telegram_bot.py` — основной бот (`@ELMA_Connector_bot`): принимает вопросы, роутит по категориям, отвечает
- `bot/admin_bot.py` — аудитор (`@Helper_elma_bot`): раз в час проверяет качество ответов, шлёт отчёт администратору с кнопками

Данные из ELMA365 хранятся локально в `data/` (JSON-кэш). Бот читает кэш, не обращаясь к API при каждом вопросе.

---

## Структура репозитория

```
ELMA_Connector/
├── bot/
│   ├── telegram_bot.py       # Основной бот — точка входа
│   ├── admin_bot.py          # Аудитор — точка входа
│   ├── core/
│   │   ├── claude_client.py  # Роутер + ROUTABLE_CATEGORIES + вызов AI
│   │   ├── aggregator.py     # Агрегаторы данных по каждой категории
│   │   ├── auditor.py        # Логика аудита ответов
│   │   └── agent_manager.py  # Управление субагентами
│   └── agents/               # Markdown-инструкции субагентов
│       ├── kmd_agent.md
│       └── excel_agent.md
├── config/
│   └── entities.json         # Все запросы к ELMA365 (id, url, name, description, routing_hints)
├── data/                     # Локальный кэш данных из ELMA (не в git)
├── scripts/
│   ├── load/load_data.py     # Загрузчик данных из ELMA API
│   ├── check/                # Скрипты диагностики
│   └── run.ps1               # Единая точка входа для типовых задач
├── dashboards/               # Готовые HTML-дашборды
├── .env                      # Токены (не в git)
└── .claude/
    ├── agents/               # Кастомные агенты Claude Code
    └── skills/               # Скиллы Claude Code
```

---

## Первый запуск

### 1. Создать `.env` в корне проекта
```
ELMA_TOKEN=...
ELMA_BASE_URL=https://dlqixw6ehyxiy.elma365.ru/pub/v1/app
TELEGRAM_BOT_TOKEN=...
ADMIN_BOT_TOKEN=...
ADMIN_CHAT_ID=...
GROQ_API_KEY=...
```

### 2. Установить зависимости
```bash
pip install -r requirements.txt
pip install -r bot/requirements.txt
```

### 3. Загрузить данные из ELMA
```powershell
.\scripts\run.ps1 load
```

### 4. Запустить боты
```bash
# Основной бот
python bot/telegram_bot.py

# Аудитор (в отдельном терминале)
python bot/admin_bot.py
```

---

## Обновление данных из ELMA

```powershell
# Все сущности
.\scripts\run.ps1 load

# Конкретная сущность по id из entities.json
.\scripts\run.ps1 load zadanie_na_kmd
.\scripts\run.ps1 load zns_po_kmd
```

Данные сохраняются в `data/`. Слепки для отслеживания изменений — в `data/.snapshots/`.

---

## Как устроен роутер

Роутер находится в `bot/core/claude_client.py` — список `ROUTABLE_CATEGORIES`:

```python
ROUTABLE_CATEGORIES = [
    'zadanie_na_kmd',      # Задания КМД
    'dop_kmd',             # Дополнительные задания КМД
    'kartochka_vitrazha_po_km',  # Карточки витражей
    'zns_po_kmd',          # ЗНС (снабжение)
]
```

Роутер берёт `routing_hints` из `config/entities.json` и определяет к какой категории относится вопрос пользователя.

**Добавить новую категорию:**
1. Добавить запрос в `entities.json` с полем `routing_hints` (ключевые слова через запятую)
2. Добавить id в `ROUTABLE_CATEGORIES` в `claude_client.py`
3. Добавить агрегатор в `bot/core/aggregator.py`
4. Использовать скилл `elma-rules-update` для добавления нового запроса к ELMA

---

## Проверка ошибок

```powershell
# Логи основного бота (если запущен через run.ps1)
Get-Content bot_out.txt -Tail 50
Get-Content bot_err.txt -Tail 50

# Скрипты диагностики
python scripts/check/check_auditor.py
python scripts/check/check_changes.py
```

Аудитор (`@Helper_elma_bot`) сам присылает отчёты об ошибках раз в час — проверяй его в Telegram.

---

## Публикация изменений на GitHub

```bash
# Проверить статус
git status

# Добавить изменения
git add .
git commit -m "описание изменений"
git push
```

Токены и данные защищены `.gitignore` — в репозиторий не попадут.

---

## Связанные скиллы

- `elma-rules-update` — добавить новый запрос к ELMA365 API в правила проекта
