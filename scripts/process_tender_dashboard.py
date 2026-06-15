import json
from datetime import datetime
from collections import defaultdict

with open('data/tender.json', 'r', encoding='utf-8') as f:
    tenders = json.load(f)['result']['result']
with open('data/raboty_po_tenderu.json', 'r', encoding='utf-8') as f:
    raboty = json.load(f)['result']['result']
with open('data/users.json', 'r', encoding='utf-8') as f:
    users_data = json.load(f)['result']['result']

# Load status definitions
status_names = {}
for fname in ['data/statusy.json', 'data/statusy_rabot_po_tenderam.json']:
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            st = json.load(f)
        for item in st.get('statusItems', []):
            status_names[item['id']] = item['name']
    except:
        pass

user_names = {}
for u in users_data:
    fn = u.get('fullname', {})
    last = fn.get('lastname', '')
    first = fn.get('firstname', '')
    middle = fn.get('middlename', '')
    parts = [last]
    if first:
        parts.append(first[0] + '.')
        if middle:
            parts[-1] += middle[0] + '.'
    user_names[u['__id']] = ' '.join(parts)

raboty_by_tender = defaultdict(list)
for rb in raboty:
    if rb.get('tender'):
        for tid in rb['tender']:
            raboty_by_tender[tid].append(rb)

type_full = {
    'vt_vitrazhi_tyoplye': 'ВТ — Витражи Тёплые',
    'vkh_vitrazhi_kholodnye': 'ВХ — Витражи Холодные',
    'tkh_vitrazhi_tyoplo-kholodnye': 'ТХ — Витражи Тёпло-Холодные',
    'vf_ventiliruemye_fasady': 'ВФ — Вентилируемые Фасады',
    'mf_mokrye_fasady_shtukaturnye': 'МФ — Мокрые Фасады',
    'pkh_pvkh-konstrukcii_metalloplastik': 'ПХ — ПВХ-конструкции',
    'sp_sendvich-paneli': 'СП — Сэндвич-Панели',
    'sk_steklyannye_kozyrki': 'СК — Стеклянные Козырьки',
    'km_kassety_metallicheskie': 'КМ — Кассеты Металлические',
    'pm_-_postavka_materialov': 'ПМ — Поставка материалов',
    'pr_prochee': 'ПР — Прочее',
    'rm_remontnye_raboty': 'РМ — Ремонтные работы',
    's_stekloizdeliya': 'С — Стеклоизделия',
    'kk_kassety_kompozitnye': 'КК — Кассеты Композитные',
    'vo_vitrazh_obrazec': 'ВО — Витражи Образец',
}

type_short = {k: v.split(' — ')[0] for k, v in type_full.items()}

rows = []
for t in tenders:
    if not t.get('tipy_rabot'):
        continue
    created = t.get('__createdAt')
    if not created:
        continue
    try:
        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
    except:
        continue

    inits = t.get('iniciator_rabot_1', [])
    init_names = [user_names.get(iid, iid[:8]) for iid in inits]
    init_key = '; '.join(init_names)

    linked = raboty_by_tender.get(t['__id'], [])
    total_kv = 0
    total_summa = 0
    total_stoim = 0

    for rb in linked:
        if rb.get('kvadratura'):
            total_kv += rb['kvadratura']
        if rb.get('itogovaya_summa_tendera') and rb['itogovaya_summa_tendera'].get('cents'):
            total_summa += rb['itogovaya_summa_tendera']['cents'] / 100
        if rb.get('stoimost_kontrakta') and rb['stoimost_kontrakta'].get('cents'):
            total_stoim += rb['stoimost_kontrakta']['cents'] / 100

    if total_summa == 0 and t.get('itogovaya_summa_tendera') and t['itogovaya_summa_tendera'].get('cents'):
        total_summa = t['itogovaya_summa_tendera']['cents'] / 100

    st_id = t.get('__status', {}).get('status')
    st_name = status_names.get(st_id, 'Неизвестно') if st_id else 'Неизвестно'
    st_order = t.get('__status', {}).get('order', 0)

    for tr in t['tipy_rabot']:
        code = tr.get('code', '')
        rows.append({
            'y': dt.year,
            'm': dt.month,
            'tc': code,
            'tn': type_full.get(code, code),
            'ts': type_short.get(code, code),
            'ii': init_key,
            'si': st_name,
            'so': st_order,
            'kv': round(total_kv, 2),
            'rr': round(total_summa, 2),
            'kr': round(total_stoim, 2),
        })

status_order = {v: k for k, v in status_names.items()}
output = {
    'rows': rows,
    'type_names': type_full,
    'type_short': type_short,
    'inits': sorted(set(r['ii'] for r in rows if r['ii'])),
    'statuses': sorted(set(r['si'] for r in rows if r['si']), key=lambda x: status_order.get(x, 99)),
}

with open('data/tender_dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False)

print(f'Saved {len(rows)} rows, {len(output["inits"])} initiators')
