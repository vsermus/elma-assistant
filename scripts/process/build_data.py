import json
from collections import Counter

STATUS_NAMES = {
    1: 'Создан', 3: 'В работе с КМД', 4: 'Выполнение строительства',
    5: 'Статус 5', 6: 'Завершен', 7: 'Закрыт успешно',
    8: 'На согласовании', 9: 'Предварительный расчет',
    10: 'Претендуем на тендер', 11: 'Тендер выигран',
    12: 'Участвуем в тендере', 13: 'Участвовали в тендере',
    14: 'Выход на тендер'
}

with open('data/works/all_works_with_status.json', 'r', encoding='utf-8-sig') as f:
    raw = json.load(f)
items = raw['result']['result']
print(f'Total work items: {len(items)}')

# Load tender headers for names
with open('data/tender/all_tenders.json', 'r', encoding='utf-8-sig') as f:
    tenders_raw = json.load(f)
tender_list = tenders_raw if isinstance(tenders_raw, list) else tenders_raw.get('result', [])
if isinstance(tender_list, dict):
    tender_list = tender_list.get('result', []) or tender_list.get('items', [])

tender_map = {}
for t in tender_list:
    if isinstance(t, dict):
        tid = t.get('__id') or t.get('id')
        if tid:
            tender_map[tid] = t
print(f'Tenders: {len(tender_map)}')

output = []
status_count = Counter()

for item in items:
    st = item.get('__status', {})
    status_id = st.get('status') if isinstance(st, dict) else None
    status_name = STATUS_NAMES.get(status_id, f'Статус {status_id}')
    if not status_id:
        continue

    # Type info
    tip_code = ''
    tip_name = ''
    tip_rabot = item.get('tip_rabot_po_tenderu', [])
    if tip_rabot and isinstance(tip_rabot, list) and len(tip_rabot) > 0:
        if isinstance(tip_rabot[0], dict):
            tip_code = tip_rabot[0].get('code', '')
            tip_name = tip_rabot[0].get('name', '')
    if not tip_code:
        tip_code = item.get('tip_code', '')
        tip_name = item.get('tip_name', '')
    
    if tip_code == 'postavka_materialov':
        tip_code = 'pm_-_postavka_materialov'

    if not tip_code:
        continue

    # Area: ploshad_konstrukcii_v_tendere_m2 (primary), kvadratura (fallback)
    area = item.get('ploshad_konstrukcii_v_tendere_m2') or item.get('kvadratura') or 0
    if isinstance(area, str):
        area = 0
    area = float(area)

    # Sum: itogovaya_summa_tendera (primary)
    sum_field = item.get('itogovaya_summa_tendera', {})
    summa = 0
    if isinstance(sum_field, dict) and sum_field.get('cents'):
        summa = sum_field['cents'] / 100.0
    elif isinstance(sum_field, (int, float)):
        summa = float(sum_field)
    
    # Fallback: dokhod_ot_okazaniya_uslug_m2 * area
    if summa == 0 and area > 0:
        dokhod_m2 = item.get('dokhod_ot_okazaniya_uslug_m2', {})
        if isinstance(dokhod_m2, dict) and dokhod_m2.get('cents'):
            rate = dokhod_m2['cents'] / 100.0
            summa = rate * area
    
    # Fallback: stoimost_za_m2_v_tender * area
    if summa == 0 and area > 0:
        cena_m2 = item.get('stoimost_za_m2_v_tender')
        if cena_m2 and isinstance(cena_m2, (int, float)):
            summa = cena_m2 * area
    
    # Fallback: stoimost_kontrakta
    if summa == 0:
        kontr = item.get('stoimost_kontrakta', {})
        if isinstance(kontr, dict) and kontr.get('cents'):
            summa = kontr['cents'] / 100.0

    # Name
    name = item.get('kratkoe_nazvanie_obekta', '') or item.get('__name', '')
    name = name.strip() if name else ''
    
    # Date
    date = item.get('__createdAt', '')

    # Executors in TEO
    executors = item.get('otvetstvennyi_v_teo', [])
    if not isinstance(executors, list):
        executors = [executors] if executors else []

    status_count[status_id] += 1
    output.append({
        'id': item.get('__id', ''),
        'name': name,
        'tip_code': tip_code,
        'tip_name': tip_name,
        'kvadratura': round(area, 2),
        'summa': round(summa, 2),
        'date': date,
        'status_id': status_id,
        'status_name': status_name,
        'executors': executors
    })

print(f'\nProcessed: {len(output)}')
print(f'Status distribution:')
for sid, cnt in sorted(status_count.items(), key=lambda x: -x[1]):
    items_s = [d for d in output if d['status_id'] == sid]
    with_area = sum(1 for d in items_s if d['kvadratura'] > 0)
    with_sum = sum(1 for d in items_s if d['summa'] > 0)
    print(f'  {sid:2d} ({STATUS_NAMES.get(sid,"?"):25s}): {cnt:4d} items, area>0: {with_area:4d}, sum>0: {with_sum:4d}')

# Save
with open('data/tender/all_tenders_consolidated.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {len(output)} records')
