import json
from datetime import datetime
from collections import defaultdict

STATUS_NAMES = {
    10: "Новый",
    1: "РОП",
    2: "КОП",
    3: "РП",
    4: "Согласован",
    8: "Заведение в 1С",
    9: "Завершено",
    7: "Без статуса"
}

with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\data\ozm.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data.get('result', {}).get('result', [])
print(f"Всего записей: {len(records)}")

# Check for status 7
status_counts_raw = defaultdict(int)
for r in records:
    s = r.get("__status", {})
    if isinstance(s, dict):
        st = s.get("status")
    else:
        st = None
    status_counts_raw[st] += 1
print(f"Распределение по статусам (сырое): {dict(status_counts_raw)}")

# Check for all unique status codes
all_statuses = set()
for r in records:
    s = r.get("__status", {})
    if isinstance(s, dict):
        all_statuses.add(s.get("status"))
    else:
        all_statuses.add(None)
print(f"Все уникальные статусы: {all_statuses}")

# Check deleted
deleted_count = sum(1 for r in records if r.get("__deletedAt"))
print(f"Удалённых: {deleted_count}")

# Check metrazh with none
none_metrazh = sum(1 for r in records if r.get("metrazh") is None)
print(f"metrazh = null: {none_metrazh}")

# Check est_raskhozhdeniya values
disp_counts = defaultdict(int)
for r in records:
    v = r.get("est_raskhozhdeniya_v_ozm_i_tendernoi_dokumentacii")
    disp_counts[str(v)] += 1
print(f"est_raskhozhdeniya: {dict(disp_counts)}")

# Check date range
dates = []
for r in records:
    dt = r.get("__createdAt")
    if dt:
        try:
            dates.append(datetime.fromisoformat(dt.replace("Z", "+00:00")))
        except:
            pass
if dates:
    print(f"Диапазон дат: {min(dates)} - {max(dates)}")
