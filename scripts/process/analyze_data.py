import json
from collections import Counter

with open('data/works/all_works_with_status.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

print(f'Top keys: {list(data.keys())}')
result = data.get('result')
print(f'result type: {type(result).__name__}')
print(f'result keys: {list(result.keys()) if isinstance(result, dict) else "N/A"}')

if isinstance(result, dict):
    for k, v in result.items():
        if isinstance(v, list):
            print(f'  key "{k}" is list of {len(v)} items')
            items = v
            break
else:
    items = []

st_count = 0
state_count = 0
for item in items[:10]:
    if isinstance(item, str):
        print(f'String item: {item[:100]}')
        continue
    st = item.get('__status')
    ts = item.get('tender_state')
    rt = item.get('rezultat_tendera')
    print(f'  id={item.get("__id","?")[:12]} state={ts} status={st} rez={rt}')

# Full scan
st_all = 0
state_vals = Counter()
for item in items:
    st = item.get('__status')
    if st and isinstance(st, dict):
        st_all += 1
    ts = item.get('tender_state')
    if ts:
        state_vals[ts] += 1

print(f'\nItems with __status: {st_all}')
print('tender_state distribution:')
for k, v in state_vals.most_common():
    print(f'  [{k}] = {v}')
