import json

with open('data/tender/all_tenders_consolidated.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for i in range(3):
    item = data[i]
    name = item['tip_name']
    code = item['tip_code']
    print(f'Code: {code}')
    print(f'Name: {name}')
    print(f'Name bytes: {name.encode("utf-8").hex()}')
    print()
