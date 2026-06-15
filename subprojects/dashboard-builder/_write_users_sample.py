import json
with open('data/users.json', encoding='utf-8') as f:
    data = json.load(f)
records = data['result']['result']
with open('subprojects/dashboard-builder/_users_sample.txt', 'w', encoding='utf-8') as out:
    for i, r in enumerate(records[:5]):
        out.write(f'Запись {i+1}:\n')
        out.write(f'  __name: {r["__name"]}\n')
        fn = r['fullname']
        out.write(f'  fullname.lastname: {fn["lastname"]}\n')
        out.write(f'  fullname.firstname: {fn["firstname"]}\n')
        out.write(f'  fullname.middlename: {fn["middlename"]}\n')
        out.write(f'\n')
