import json
with open('data/users/users.json', 'r', encoding='utf-8-sig') as f:
    raw = json.load(f)
result = raw['result']
print('result keys:', list(result.keys()))
items = result['result']
print('type:', type(items).__name__)
if isinstance(items, list):
    print('len:', len(items))
    for i, item in enumerate(items[:5]):
        print(f'[{i}] type={type(item).__name__}', end='')
        if isinstance(item, dict):
            uid = item.get('__id', '') or item.get('id', '') or ''
            name = item.get('fullName', '') or item.get('name', '') or ''
            print(f' id={uid[:20]} name={name[:30]}')
        elif isinstance(item, str):
            print(f' val={item[:50]}')
