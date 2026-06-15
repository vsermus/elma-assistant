import json
from collections import Counter

with open('data/works/all_works_with_status.json', 'r', encoding='utf-8-sig') as f:
    raw = json.load(f)
items = raw['result']['result']

# Check all fields that contain area/square info
all_fields = Counter()
for item in items:
    for k in item.keys():
        if isinstance(item[k], dict) or item[k] or item[k] == 0:
            all_fields[k] += 1

# Show only area-related fields
area_fields = [k for k in all_fields if any(x in k.lower() for x in ['ploshad', 'kvadrat', 'square', 'm2', 'm_2'])]
print('Area-related fields and their fill counts:')
for f in sorted(area_fields):
    kv = sum(1 for item in items if item.get(f) is not None and item.get(f) != '' and item.get(f) != 0)
    non_zero = sum(1 for item in items if item.get(f) not in (None, '', 0, {}, []))
    print(f'  {f:45s}: {non_zero:4d} non-empty')

# Also look for sum/cost fields
print('\nSum/cost fields:')
sum_fields = [k for k in all_fields if any(x in k.lower() for x in ['summa', 'stoimost', 'itogo', 'cena', 'dokhod', 'byudzhet', 'kontrakta'])]
for f in sorted(sum_fields)[:20]:
    non_zero = sum(1 for item in items if item.get(f) not in (None, '', 0, {}, []))
    print(f'  {f:45s}: {non_zero:4d} non-empty')
