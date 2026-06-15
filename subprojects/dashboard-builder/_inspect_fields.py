import json, os

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')

for eid in ['raboty_po_tenderu', 'tender', 'spravochnik_id', '_companies', 'users', 'statusy_rabot_po_tenderam']:
    path = os.path.join(ROOT, 'data', f'{eid}.json')
    if not os.path.exists(path):
        print(f'{eid}: NOT FOUND')
        continue
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    
    records = None
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        if 'result' in data and isinstance(data['result'], dict) and 'result' in data['result']:
            records = data['result']['result']
        elif 'result' in data and isinstance(data['result'], list):
            records = data['result']
        elif 'statusItems' in data:
            records = data['statusItems']
        elif 'items' in data:
            records = data['items']
    
    if not records or len(records) == 0:
        print(f'{eid}: NO RECORDS')
        continue
    
    print(f'=== {eid} ({len(records)} records) ===')
    for f in records[0].keys():
        val = records[0][f]
        vtype = type(val).__name__
        if vtype == 'dict':
            vtype = f'dict({list(val.keys())[:4]})'
        elif vtype == 'list':
            if len(val) > 0:
                vtype = f'list/{type(val[0]).__name__}'
            else:
                vtype = 'list/empty'
        print(f'  {f} ({vtype})')
    print()
