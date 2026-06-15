---
name: api-filter-updatedAt-not-working
description: Фильтрация по __updatedAt в ELMA365 API не работает — инкрементальная загрузка через API невозможна
metadata:
  type: feedback
  discovered: 2026-06-04
---

Фильтрация по полю `__updatedAt` в ELMA365 API не работает — сервер принимает запрос без ошибки, но молча игнорирует условие и возвращает все записи.

**Проверенные форматы — все не работают:**
- `{"size": 10000, "conditions": [{"field": "__updatedAt", "operator": "gt", "value": "..."}]}`
- `{"size": 10000, "where": "__updatedAt > \"...\""}` 
- `{"size": 10000, "active": {"field": "__updatedAt", "operator": "greater", "value": "..."}}` — возвращает 400

**Проверено на:** `zadanie_na_kmd` (936 записей), `users` (181 запись).

**Вывод:** инкрементальная загрузка через API невозможна. Всегда грузим полностью (`{"size": 10000}`). Отслеживание изменений — только через `check_changes.py` после полной загрузки.
