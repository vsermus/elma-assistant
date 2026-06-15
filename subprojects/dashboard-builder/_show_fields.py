import json
with open('data/users.json', encoding='utf-8') as f:
    data = json.load(f)
records = data['result']['result']
for i, r in enumerate(records[:3]):
    print(f'Record {i+1}:')
    print(f'  __name: {r["__name"]}')
    print(f'  fullname: {r["fullname"]}')
    print()
