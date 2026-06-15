import json

with open('data/zns_po_kmd.json', encoding='utf-8') as f:
    d = json.load(f)
    items = d['result']['result']

# search for fields containing kharakteristika, zapolneniye, etc
item = items[0]
print('=== ПОИСК ПОЛЕЙ ===')
for k in item.keys():
    kl = k.lower()
    if any(w in kl for w in ['kharakter', 'характер', 'zapol', 'заполн', 'spec', 'спец', 'opis', 'опис', 'komment', 'коммент', 'prim', 'прим', 'dop', 'доп', 'svoi', 'свой']):
        print(f'  {k}: {item[k]}')

# also check all keys for any match with "характеристика"
print('\n=== ВСЕ КЛЮЧИ ===')
for k in sorted(item.keys()):
    print(f'  {k}')
