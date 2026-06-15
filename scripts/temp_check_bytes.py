with open('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/data/zadanie_na_kmd.json', 'rb') as f:
    raw = f.read()

import re

rp_id = b'965e88d6-42ce-4c12-b388-ab4fd5fde141'
# Find all records where rp contains Zabolotsky, not deleted, status=2
# Simple approach: iterate through all records by finding __id markers
items = raw.split(b'{\r\n        "__id"')
for item in items:
    if len(item) < 50:
        continue
    check = b'"__id"' + item if not item.startswith(b'"__id"') else item
    
    # Check if rp contains our user
    idx_rp = item.find(rb'"rp"') 
    if idx_rp < 0:
        continue
    # Check if rp array contains the user id
    if rp_id not in item:
        continue
    
    # Check not deleted
    if b'"__deletedAt"' in item and b'null' not in item[item.find(b'"__deletedAt"'):item.find(b'"__deletedAt"')+30]:
        continue
    
    # Check status = 2 (in work)
    status_match = re.search(rb'"__status"\s*:\s*\{[^}]*"status"\s*:\s*2', item)
    if not status_match:
        continue
    
    # Extract name
    name_m = re.search(rb'"__name"\s*:\s*"((?:[^"\\]|\\.)*)"', item)
    if name_m:
        n = name_m.group(1).replace(b'\\"', b'"')
        name_cp1251 = n.decode('cp1251', errors='replace')
        name_utf8 = n.decode('utf-8', errors='replace')
        print('CP1251:', name_cp1251)
        print('UTF8:', repr(name_utf8))
        print('---')

    # Extract object id
    obj_m = re.search(rb'"id_proekta"\s*:\s*\[\s*"([^"]+)"', item)
    if obj_m:
        print('Object:', obj_m.group(1).decode())
        print('---')
