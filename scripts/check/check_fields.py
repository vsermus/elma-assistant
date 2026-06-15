import json
from collections import Counter

with open('data/works/all_works_with_status.json', 'r', encoding='utf-8-sig') as f:
    raw = json.load(f)
items = raw['result']['result']

# Check what financial fields are available for non-won statuses
fields_to_check = [
    'kvadratura', 'cena_m2', 'dokhod_ot_okazaniya_uslug_m2',
    'summa_kontrakta', 'itogovaya_summa_tendera', 'tendernaya_stoimost',
    'stoimost_za_m2_v_tender', 'stoimost_m2_v_kontrakte',
    'dokhod_ot_okazaniya_uslug', 'cena_m2'
]

# Find non-won items (status != 11) that have some financial data
non_won_with_data = []
for item in items:
    st = item.get('__status', {})
    sid = st.get('status') if isinstance(st, dict) else None
    if sid and sid != 11:
        has_data = False
        info = {'__id': item.get('__id',''), 'status': sid}
        for f in fields_to_check:
            val = item.get(f)
            if val and val != 0:
                if isinstance(val, dict) and 'cents' in val:
                    if val['cents'] != 0:
                        info[f] = val['cents'] / 100
                        has_data = True
                elif isinstance(val, (int, float)) and val != 0:
                    info[f] = val
                    has_data = True
                elif isinstance(val, str) and val:
                    info[f] = val[:30]
                    has_data = True
        if has_data:
            # Also check kvadratura
            kv = item.get('kvadratura') or 0
            if kv > 0:
                non_won_with_data.append(info)

print(f'Non-won items with some financial data AND area: {len(non_won_with_data)}')
for nd in non_won_with_data[:20]:
    print(f'  status={nd["status"]}, id={nd["__id"][:12]}')
    for k, v in nd.items():
        if k in ('__id', 'status'):
            continue
        print(f'    {k}: {v}')

# Also show what fields are populated for status 6 items
print('\n\nStatus 6 (Completed) - available fields with values:')
status6 = [item for item in items if isinstance(item.get('__status', {}), dict) and item['__status'].get('status') == 6]
print(f'Total status 6 items: {len(status6)}')

field_counts = Counter()
for item in status6:
    for f in fields_to_check + ['tip_code', 'tip_name']:
        val = item.get(f)
        if val is not None and val != '' and val != 0 and val != [] and val != {}:
            if isinstance(val, dict):
                if val.get('cents') and val['cents'] != 0:
                    field_counts[f] += 1
                elif val.get('currency'):
                    continue
            else:
                field_counts[f] += 1

for f, cnt in field_counts.most_common():
    print(f'  {f}: {cnt}')
