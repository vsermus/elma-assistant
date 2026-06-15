import json
from collections import Counter

with open('data/tender/all_tenders_consolidated.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total: {len(data)}')

# Tip codes
tips = Counter(item['tip_code'] for item in data)
print(f'\nUnique tip codes: {len(tips)}')
for code, cnt in tips.most_common():
    name = next((item['tip_name'] for item in data if item['tip_code'] == code), '')
    print(f'  {code}: {cnt} ({name})')

# Empty tip_code
no_code = [item for item in data if not item['tip_code']]
print(f'\nWithout tip_code: {len(no_code)}')

# Check summa distribution
nonzero_sum = [item for item in data if item['summa'] > 0]
print(f'With summa > 0: {len(nonzero_sum)}')

# Status names encoding fix - extract actual names from data
statuses = {}
for item in data:
    sid = item['status_id']
    name = item['status_name']
    if sid not in statuses:
        statuses[sid] = name

print(f'\nStatus names from data:')
for sid in sorted(statuses.keys()):
    print(f'  {sid}: "{statuses[sid]}"')
