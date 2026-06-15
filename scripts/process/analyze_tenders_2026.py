import json, urllib.request, urllib.parse
from collections import Counter, defaultdict

BASE_URL = 'https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/tender/raboty_po_tenderu_1/list'
TOKEN = '2ad06f66-6ecc-42b3-9bf4-1ef21eabb371'
STATUS_MAP = {
    1: 'Создан', 3: 'В работе с КМД', 4: 'Выполнение строительства',
    5: 'Статус 5', 6: 'Завершён', 7: 'Закрыт успешно',
    8: 'На согласовании', 9: 'Предварительный расчет',
    10: 'Претендуем на тендер', 11: 'Тендер выигран',
    12: 'Участвуем в тендере', 13: 'Участвовали в тендере',
    14: 'Выход на тендер'
}

# --- 1. Fetch all tenders from API ---
print('Fetching tenders...')
params = urllib.parse.urlencode({'query': json.dumps({"size": 10000})})
req = urllib.request.Request(f'{BASE_URL}?{params}',
    headers={'Authorization': f'Bearer {TOKEN}'})
with urllib.request.urlopen(req, timeout=60) as resp:
    tenders_raw = json.loads(resp.read().decode('utf-8'))

tenders = tenders_raw['result']['result']
print(f'Loaded {len(tenders)} tenders')

# --- 2. Load users ---
with open('data/users/users.json', 'r', encoding='utf-8-sig') as f:
    users_raw = json.load(f)
users_list = users_raw['result']['result']
users_map = {}
for u in users_list:
    if isinstance(u, dict):
        uid = u.get('__id') or u.get('id')
        if uid:
            name = u.get('fullName') or u.get('name') or u.get('email', '') or uid[:12]
            users_map[uid] = name
print(f'Loaded {len(users_map)} users')

# --- 3. Load works for tender-work relationship ---
with open('data/works/all_works_with_status.json', 'r', encoding='utf-8-sig') as f:
    works_raw = json.load(f)
works_items = works_raw['result']['result']
tenders_with_works = set()
for w in works_items:
    t = w.get('tender', [])
    if isinstance(t, list):
        for tid in t:
            if tid:
                tenders_with_works.add(tid)
    elif t:
        tenders_with_works.add(t)
print(f'Tenders with works: {len(tenders_with_works)}')

# --- 4. Filter 2026 ---
tenders_2026 = []
for t in tenders:
    created = t.get('__createdAt', '')
    if created and created.startswith('2026'):
        tenders_2026.append(t)
print(f'Tenders in 2026: {len(tenders_2026)}')

# --- 5. Analyses ---
# 5a. Status distribution
status_counts = Counter()
for t in tenders_2026:
    st = t.get('__status', {})
    sid = st.get('status') if isinstance(st, dict) else None
    status_counts[sid] += 1

# 5b. Result distribution
rezultat_counts = Counter()
for t in tenders_2026:
    r = t.get('rezultat_tendera')
    if r is True:
        rezultat_counts['Выигран'] += 1
    elif r is False:
        rezultat_counts['Проигран'] += 1
    else:
        rezultat_counts['Без результата'] += 1

# 5c. By initiators
initiator_counts = Counter()
for t in tenders_2026:
    inits = t.get('iniciator_rabot_1', [])
    if isinstance(inits, str):
        inits = [inits] if inits else []
    for uid in inits:
        if uid and isinstance(uid, str):
            initiator_counts[uid] += 1

# 5d. By RP
rp_counts = Counter()
for t in tenders_2026:
    rps = t.get('rukovoditel_proekta', [])
    if rps is None:
        rps = []
    if isinstance(rps, str):
        rps = rps.split() if rps.strip() else []
    for uid in rps:
        if uid and isinstance(uid, str):
            rp_counts[uid] += 1

# 5e. Tenders without works
tender_ids_2026 = {t.get('__id', '') for t in tenders_2026}
no_works = [t for t in tenders_2026 if t.get('__id', '') not in tenders_with_works]

# --- 6. Generate HTML ---
def user_name(uid):
    return users_map.get(uid, uid[:12] + '...')

def status_name(sid):
    return STATUS_MAP.get(sid, f'Статус {sid}')

status_rows = ''.join(
    f'<tr><td>{status_name(sid)}</td><td class="num">{cnt}</td></tr>'
    for sid, cnt in sorted(status_counts.items(), key=lambda x: -x[1])
)

rezultat_rows = ''.join(
    f'<tr><td>{k}</td><td class="num">{v}</td></tr>'
    for k, v in sorted(rezultat_counts.items(), key=lambda x: -x[1])
)

initiator_rows = ''.join(
    f'<tr><td>{user_name(uid)}</td><td class="num">{cnt}</td></tr>'
    for uid, cnt in initiator_counts.most_common()
)

rp_rows = ''.join(
    f'<tr><td>{user_name(uid)}</td><td class="num">{cnt}</td></tr>'
    for uid, cnt in rp_counts.most_common()
)

no_works_rows = ''.join(
    f'<tr><td>{t.get("__id","")[:12]}...</td><td>{t.get("kratkoe_nazvanie_obekta","?")}</td>'
    f'<td>{status_name(t.get("__status",{}).get("status"))}</td></tr>'
    for t in no_works[:50]
)
no_works_more = ''
if len(no_works) > 50:
    no_works_more = f'<tr><td colspan="3" style="color:#888;">...и ещё {len(no_works)-50} тендеров</td></tr>'

total_2026 = len(tenders_2026)

from datetime import datetime
now_str = datetime.now().strftime('%d.%m.%Y %H:%M')

html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Анализ тендеров 2026</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; padding: 30px; }}
h1 {{ font-size: 24px; margin-bottom: 8px; }}
.date {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
.blocks {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.block {{ background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.block .num {{ font-size: 32px; font-weight: 700; color: #1a237e; }}
.block .lbl {{ font-size: 13px; color: #888; margin-top: 4px; }}
.section {{ background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 20px; }}
.section h2 {{ font-size: 18px; margin-bottom: 14px; color: #1a237e; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ text-align: left; padding: 10px 12px; background: #f5f7fa; border-bottom: 2px solid #e0e0e0; font-weight: 600; color: #555; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
tr:hover td {{ background: #f8f9ff; }}
.two-cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 700px) {{ .two-cols {{ grid-template-columns: 1fr; }} body {{ padding: 16px; }} }}
</style>
</head>
<body>
<h1>Анализ тендеров за 2026 год</h1>
<p class="date">Сформировано: {now_str}</p>

<div class="blocks">
<div class="block"><div class="num">{total_2026}</div><div class="lbl">Всего тендеров в 2026</div></div>
<div class="block"><div class="num">{len(no_works)}</div><div class="lbl">Тендеров без работ</div></div>
<div class="block"><div class="num">{len(initiator_counts)}</div><div class="lbl">Уникальных инициаторов</div></div>
<div class="block"><div class="num">{len(rp_counts)}</div><div class="lbl">Назначено РП</div></div>
</div>

<div class="two-cols">
<div class="section">
<h2>Статусы тендеров</h2>
<table><thead><tr><th>Статус</th><th class="num">Кол-во</th></tr></thead><tbody>{status_rows}</tbody></table>
</div>

<div class="section">
<h2>Результаты тендеров</h2>
<table><thead><tr><th>Результат</th><th class="num">Кол-во</th></tr></thead><tbody>{rezultat_rows}</tbody></table>
</div>
</div>

<div class="two-cols">
<div class="section">
<h2>По инициаторам</h2>
<table><thead><tr><th>Инициатор</th><th class="num">Кол-во</th></tr></thead><tbody>{initiator_rows}</tbody></table>
</div>

<div class="section">
<h2>По руководителям проектов</h2>
<table><thead><tr><th>РП</th><th class="num">Кол-во</th></tr></thead><tbody>{rp_rows}</tbody></table>
</div>
</div>

<div class="section">
<h2>Тендеры без работ ({len(no_works)})</h2>
<table><thead><tr><th>ID</th><th>Объект</th><th>Статус</th></tr></thead><tbody>{no_works_rows}{no_works_more}</tbody></table>
</div>

</body>
</html>'''

with open('reports/tender_analysis_2026.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Report saved: reports/tender_analysis_2026.html')
print(f'Total 2026 tenders: {total_2026}')
print(f'Statuses: {dict(status_counts)}')
print(f'Tenders without works: {len(no_works)}')
print(f'Unique initiators: {len(initiator_counts)}')
print(f'Unique RPs: {len(rp_counts)}')
