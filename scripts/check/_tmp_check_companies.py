import json

c = json.load(open('data/companies.json', encoding='utf-8-sig'))
items = c['result']['result']

# Load users for displaying names
u = json.load(open('data/users/users.json', encoding='utf-8-sig'))
users = {i['__id']: i.get('fullname', {}) for i in u['result']['result']}

def user_name(uid):
    fn = users.get(uid, {})
    parts = [fn.get('lastname', '')]
    if fn.get('firstname'):
        first = fn['firstname'][0] + '.'
        parts.append(first)
        if fn.get('middlename'):
            parts[-1] += fn['middlename'][0] + '.'
    return ' '.join(parts) if parts else uid

cnt = 0
by_creator = {}
created_before_2026 = 0

for i in items:
    created = i.get('__createdAt', '')
    creator = i.get('__createdBy', '')
    if created and created.startswith('2026'):
        cnt += 1
        by_creator[creator] = by_creator.get(creator, 0) + 1
        if len(by_creator) <= 250:
            pass

print(f"Всего компаний в системе: {len(items)}")
print(f"Из них создано в 2026 году: {cnt}")

if cnt > 0:
    total_by_user = sum(by_creator.values())
    print(f"\nКто создавал (всего {len(by_creator)} человек):")
    for uid, n in sorted(by_creator.items(), key=lambda x: -x[1])[:20]:
        name = user_name(uid)
        print(f"  {name:25s} — {n:4d} компаний ({n*100//total_by_user}%)")

    # Unknown creators
    unknown = [uid for uid in by_creator if uid not in users]
    if unknown:
        print(f"\n  Ещё {len(unknown)} создателей не найдены в справочнике пользователей")
else:
    pass

# If 0, check what dates exist
if cnt == 0:
    years = set()
    for i in items:
        created = i.get('__createdAt', '')
        if created and len(created) >= 4:
            years.add(created[:4])
    print(f"Годы создания: {sorted(years)}")
