"""
Загрузчик данных из ELMA365 API.

Использование:
  python scripts/load/load_data.py              # загрузить все сущности
  python scripts/load/load_data.py users        # загрузить только users
  python scripts/load/load_data.py users tender # загрузить users и tender

Конфиг сущностей: config/entities.json
Токен: .env (ELMA_TOKEN)
"""

import json
import os
import sys
import urllib.request, urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

LOAD_LOG_PATH = os.path.join(config.DATA_DIR, "load_log.json")


def load_env():
    token = None
    if not os.path.exists(config.ENV_PATH):
        print(f"  [WARN] .env not found at {config.ENV_PATH}")
        return token
    with open(config.ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("ELMA_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        print("  [WARN] ELMA_TOKEN not found in .env")
    return token


def load_config():
    if not os.path.exists(config.ENTITIES_CONFIG):
        print(f"  [ERR] Config not found: {config.ENTITIES_CONFIG}")
        sys.exit(1)
    with open(config.ENTITIES_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_entity(url, token):
    # URL-encode the query parameter (JSON с {,}, пробелами и т.д.)
    parsed = urllib.parse.urlparse(url)
    if parsed.query:
        encoded_query = urllib.parse.quote(parsed.query, safe='=&')
        url = urllib.parse.urlunparse(parsed._replace(query=encoded_query))
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8-sig"))


def save_entity(entity_id, data):
    path = os.path.join(config.DATA_DIR, f"{entity_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def count_records(data):
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("result", "statusItems", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
            elif isinstance(val, dict):
                inner = val.get("result") or val.get("items")
                if isinstance(inner, list):
                    return len(inner)
    return 0


def save_load_log(results):
    now = datetime.now().isoformat(timespec="seconds")
    log = {}
    if os.path.exists(LOAD_LOG_PATH):
        with open(LOAD_LOG_PATH, "r", encoding="utf-8") as f:
            log = json.load(f)
    for eid, entry in results.items():
        log[eid] = {**entry, "loaded_at": now}
    log["_last_load"] = now
    with open(LOAD_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def main():
    entities = load_config()
    token = load_env()
    if not token:
        print("  [ERR] No token — abort.")
        sys.exit(1)

    requested = sys.argv[1:] if len(sys.argv) > 1 else None
    if requested:
        requested = set(requested)
        entities = [e for e in entities if e["id"] in requested]
        if not entities:
            print(f"  [ERR] No matching entities for: {requested}")
            sys.exit(1)

    total = len(entities)
    ok = 0
    fail = 0
    log_results = {}

    print(f"Loading {total} entitie(s)...\n")

    for i, entity in enumerate(entities, 1):
        eid = entity["id"]
        name = entity["name"]
        url = entity["url"]
        print(f"[{i}/{total}] {name} ({eid})... ", end="", flush=True)

        try:
            data = fetch_entity(url, token)
            path = save_entity(eid, data)
            size_kb = os.path.getsize(path) / 1024
            records = count_records(data)
            print(f"OK — {records} records, {size_kb:.0f} KB")
            log_results[eid] = {"name": name, "records": records, "size_kb": round(size_kb)}
            ok += 1
        except Exception as e:
            print(f"FAIL — {e}")
            log_results[eid] = {"name": name, "error": str(e)}
            fail += 1

    save_load_log(log_results)
    print(f"\nDone: {ok} OK, {fail} FAIL of {total}")
    print(f"Лог: {LOAD_LOG_PATH}")


if __name__ == "__main__":
    main()
