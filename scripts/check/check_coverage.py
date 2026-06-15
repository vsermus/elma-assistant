import json
from collections import Counter

with open('data/tender/all_tenders_consolidated.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

STATUS_NAMES = {
    1: 'Создан', 3: 'В работе с КМД', 4: 'Выполнение строительства',
    5: 'Статус 5', 6: 'Завершен', 7: 'Закрыт успешно',
    8: 'На согласовании', 9: 'Предварительный расчет',
    10: 'Претендуем на тендер', 11: 'Тендер выигран',
    12: 'Участвуем в тендере', 13: 'Участвовали в тендере',
    14: 'Выход на тендер'
}

for sid in sorted(set(d['status_id'] for d in data)):
    items = [d for d in data if d['status_id'] == sid]
    total = len(items)
    with_area = sum(1 for d in items if d['kvadratura'] > 0)
    with_sum = sum(1 for d in items if d['summa'] > 0)
    total_area = sum(d['kvadratura'] for d in items)
    total_sum = sum(d['summa'] for d in items)
    name = STATUS_NAMES.get(sid, f'Status {sid}')
    print(f'{sid:2d} ({name:25s}): {total:4d} items, area>0: {with_area:4d}, sum>0: {with_sum:4d}, total_area={total_area:10.1f}, total_sum={total_sum:15.2f}')
