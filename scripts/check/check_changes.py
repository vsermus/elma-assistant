"""
Проверка изменений в данных ELMA365.

Сравнивает текущие JSON-файлы в data/ с предыдущими слепками:
  - Схема (набор полей)   — новые/удалённые поля
  - Данные (записи)       — новые/удалённые/обновлённые записи

Слепки хранятся в data/.snapshots/{entity_id}.json
Отчёт — data/.snapshots/last_report.json

Использование:
  python scripts/check/check_changes.py
"""

import json
import os
import sys
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

SNAPSHOTS_DIR = os.path.join(config.DATA_DIR, ".snapshots")
REPORT_FILE = os.path.join(SNAPSHOTS_DIR, "last_report.json")
NOW = datetime.now().isoformat(timespec="seconds")


def ensure_snapshots_dir():
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


def load_entities_config():
    if not os.path.exists(config.ENTITIES_CONFIG):
        print("  [ERR] config/entities.json not found")
        return []
    with open(config.ENTITIES_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_records(data):
    """Извлечь список записей из JSON любой структуры ELMA."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("statusItems", "items"):
        val = data.get(key)
        if isinstance(val, list):
            return val
    result = data.get("result")
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        inner = result.get("result")
        if isinstance(inner, list):
            return inner
    return []


def get_record_id(rec):
    """ID записи: __id или id для справочников."""
    return rec.get("__id") or rec.get("id")


def collect_fields(records):
    """Все уникальные поля среди записей."""
    fields = set()
    for rec in records:
        if isinstance(rec, dict):
            fields.update(rec.keys())
    return sorted(fields)


def collect_records_snapshot(records):
    """{id: __updatedAt} для сравнения данных."""
    snap = {}
    for rec in records:
        rid = get_record_id(rec)
        if rid:
            snap[str(rid)] = rec.get("__updatedAt") or ""
    return snap


def load_snapshot(entity_id):
    path = os.path.join(SNAPSHOTS_DIR, f"{entity_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(entity_id, snapshot):
    path = os.path.join(SNAPSHOTS_DIR, f"{entity_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False)


def compare_schema(old_fields, new_fields):
    old_set, new_set = set(old_fields), set(new_fields)
    return {
        "added": sorted(new_set - old_set),
        "removed": sorted(old_set - new_set),
    }


def compare_data(old_recs, new_recs):
    old_ids = set(old_recs.keys())
    new_ids = set(new_recs.keys())
    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = old_ids & new_ids
    updated = [rid for rid in common_ids if old_recs[rid] != new_recs[rid]]
    return {
        "added": len(added_ids),
        "removed": len(removed_ids),
        "updated": len(updated),
    }


def check_entity(entity_id, name, records):
    old_snap = load_snapshot(entity_id)
    current_fields = collect_fields(records)
    current_recs = collect_records_snapshot(records)
    current_count = len(records)

    if old_snap is None:
        # Первый замер — сохраняем, не сравниваем
        snapshot = {
            "entity_id": entity_id,
            "snapshot_date": NOW,
            "record_count": current_count,
            "fields": current_fields,
            "records": current_recs,
        }
        save_snapshot(entity_id, snapshot)
        return {"status": "initialized", "schema": None, "data": None}

    schema_diff = compare_schema(old_snap.get("fields", []), current_fields)
    data_diff = compare_data(old_snap.get("records", {}), current_recs)

    has_schema_changes = bool(schema_diff["added"] or schema_diff["removed"])
    has_data_changes = any(v > 0 for v in data_diff.values())
    status = "unchanged"
    if has_schema_changes and has_data_changes:
        status = "schema+data"
    elif has_schema_changes:
        status = "schema"
    elif has_data_changes:
        status = "data"

    # Обновляем слепок
    snapshot = {
        "entity_id": entity_id,
        "snapshot_date": NOW,
        "record_count": current_count,
        "fields": current_fields,
        "records": current_recs,
    }
    save_snapshot(entity_id, snapshot)

    return {"status": status, "schema": schema_diff, "data": data_diff}


def format_report_item(eid, name, result):
    status = result["status"]
    lines = [f"  [{eid}] {name}"]
    if status == "initialized":
        lines.append("    -> Первичный слепок создан")
        return lines

    sd = result.get("schema")
    dd = result.get("data")

    if sd and (sd["added"] or sd["removed"]):
        if sd["added"]:
            lines.append(f"    + Новые поля ({len(sd['added'])}): {', '.join(sd['added'][:10])}")
        if sd["removed"]:
            lines.append(f"    - Удалены поля ({len(sd['removed'])}): {', '.join(sd['removed'][:10])}")

    if dd and (dd["added"] or dd["removed"] or dd["updated"]):
        parts = []
        if dd["added"]:
            parts.append(f"+{dd['added']} новых")
        if dd["removed"]:
            parts.append(f"-{dd['removed']} удалено")
        if dd["updated"]:
            parts.append(f"~{dd['updated']} изменено")
        if parts:
            lines.append(f"    Записи: {', '.join(parts)}")

    if status == "unchanged":
        lines.append("    Без изменений")

    return lines


def build_report_data(eid, name, result):
    """Машинно-читаемый формат для агента."""
    entry = {"name": name, "status": result["status"]}
    sd = result.get("schema")
    dd = result.get("data")
    if sd:
        entry["new_fields"] = sd["added"]
        entry["removed_fields"] = sd["removed"]
    if dd:
        entry["new_records"] = dd["added"]
        entry["deleted_records"] = dd["removed"]
        entry["updated_records"] = dd["updated"]
    return entry


def main():
    ensure_snapshots_dir()
    entities = load_entities_config()
    if not entities:
        return

    report = {"check_date": NOW, "entities": {}}
    has_changes = False

    print(f"Проверка изменений ELMA — {NOW}\n")

    for ent in entities:
        eid = ent["id"]
        name = ent["name"]
        path = os.path.join(config.DATA_DIR, f"{eid}.json")

        if not os.path.exists(path):
            print(f"  [!] {name} ({eid}) — файл не найден, пропускаем")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = extract_records(data)
            if not records:
                print(f"  [!] {name} ({eid}) — нет записей в файле")
                continue
            result = check_entity(eid, name, records)
            report["entities"][eid] = build_report_data(eid, name, result)
            if result["status"] != "unchanged":
                has_changes = True
            for line in format_report_item(eid, name, result):
                print(line)
        except Exception as e:
            print(f"  [ERR] {name} ({eid}): {e}")

    report["has_changes"] = has_changes
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'Есть изменения!' if has_changes else 'Всё без изменений.'}")
    print(f"Отчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
