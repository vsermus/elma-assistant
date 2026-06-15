import json
with open('data/users/users.json', 'r', encoding='utf-8-sig') as f:
    raw = json.load(f)
result = raw['result']
print('result type:', type(result).__name__)
if isinstance(result, dict):
    print('result keys:', list(result.keys()))
    for k, v in result.items():
        if isinstance(v, list):
            print(f'  {k}: list of {len(v)}')
            if v:
                print(f'  first item keys: {list(v[0].keys())[:10]}')
                print(f'  id={v[0].get("__id","")}')
                print(f'  fullName={v[0].get("fullName","")}')
                print(f'  email={v[0].get("email","")}')
