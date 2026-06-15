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

# ============ Helper ============
def parse_date(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return None

def get_status_code(r):
    s = r.get("__status", {})
    if isinstance(s, dict):
        return s.get("status")
    return None

def get_metrazh(r):
    m = r.get("metrazh")
    return m if m is not None else 0

# ============ Table 1: Dynamics by year/month ============
monthly = defaultdict(lambda: {
    "count": 0,
    "total_metrazh": 0.0,
    "discrepancies": 0,
    "metrazh_values": []
})

for r in records:
    dt = parse_date(r.get("__createdAt"))
    if dt:
        key = (dt.year, dt.month)
        monthly[key]["count"] += 1
        m = get_metrazh(r)
        monthly[key]["total_metrazh"] += m
        monthly[key]["metrazh_values"].append(m)
        if r.get("est_raskhozhdeniya_v_ozm_i_tendernoi_dokumentacii") is True:
            monthly[key]["discrepancies"] += 1

table1 = []
for (year, month), vals in sorted(monthly.items()):
    avg = round(vals["total_metrazh"] / vals["count"], 2) if vals["count"] > 0 else 0
    table1.append({
        "год": year,
        "месяц": month,
        "количество": vals["count"],
        "метраж_сумма": round(vals["total_metrazh"], 2),
        "метраж_средний": avg,
        "расхождения": vals["discrepancies"]
    })

# ============ Table 2: Distribution by status ============
status_groups = defaultdict(lambda: {
    "count": 0,
    "total_metrazh": 0.0,
    "metrazh_values": []
})

for r in records:
    sc = get_status_code(r)
    status_groups[sc]["count"] += 1
    m = get_metrazh(r)
    status_groups[sc]["total_metrazh"] += m
    status_groups[sc]["metrazh_values"].append(m)

total_all = len(records)
table2 = []
for code in sorted(status_groups.keys()):
    vals = status_groups[code]
    name = STATUS_NAMES.get(code, f"Неизвестный ({code})")
    avg = round(vals["total_metrazh"] / vals["count"], 2) if vals["count"] > 0 else 0
    pct = round(vals["count"] / total_all * 100, 2) if total_all > 0 else 0
    table2.append({
        "код_статуса": code,
        "название_статуса": name,
        "количество": vals["count"],
        "метраж_сумма": round(vals["total_metrazh"], 2),
        "метраж_средний": avg,
        "доля_процентов": pct
    })

# ============ Overall statistics ============
active = sum(1 for r in records if not r.get("__deletedAt"))
deleted = sum(1 for r in records if r.get("__deletedAt"))
total_metrazh_all = sum(get_metrazh(r) for r in records)

dates = [parse_date(r.get("__createdAt")) for r in records if parse_date(r.get("__createdAt"))]
min_date = min(dates).strftime("%Y-%m-%d") if dates else None
max_date = max(dates).strftime("%Y-%m-%d") if dates else None

overall = {
    "всего_озм": len(records),
    "активных": active,
    "удалённых": deleted,
    "общий_метраж": round(total_metrazh_all, 2),
    "дата_мин": min_date,
    "дата_макс": max_date
}

# ============ Build result ============
result = {
    "таблица_1_динамика_по_годам_и_месяцам": table1,
    "таблица_2_распределение_по_статусам": table2,
    "общая_статистика": overall
}

with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\data\ozm_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Saved to ozm_analysis.json")
print(json.dumps(result, ensure_ascii=False, indent=2))
