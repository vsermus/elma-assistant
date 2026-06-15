import json, sys, os

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
query = sys.argv[1] if len(sys.argv) > 1 else '230725'

def load(name):
    path = os.path.join(DATA, name + '.json')
    raw = json.load(open(path, encoding='utf-8'))
    if isinstance(raw, list):
        return raw
    for key in ('result',):
        v = raw.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            inner = v.get('result') or v.get('items')
            if isinstance(inner, list):
                return inner
    return []

def active(recs):
    return [r for r in recs if not r.get('__deletedAt')]

sprav = active(load('spravochnik_id'))
objs = [r for r in sprav if query.lower() in str(r.get('itogovyi_id', '')).lower()
        or query.lower() in str(r.get('__name', '')).lower()]
print(f'Объект по запросу "{query}": {len(objs)} найдено')
for o in objs:
    print(f'  id={o["__id"]} itog={o.get("itogovyi_id")} name={o.get("__name")}')

if not objs:
    sys.exit()

oid = objs[0]['__id']
print(f'\nИщем допы для объекта id={oid}')

dop = active(load('dop_kmd'))
matched_dop = []
for r in dop:
    ids = r.get('id_proekta') or r.get('idp4s') or []
    if isinstance(ids, str):
        ids = [ids]
    if oid in ids:
        matched_dop.append(r)
print(f'dop_kmd записи: {len(matched_dop)}')
for r in matched_dop[:10]:
    print(f'  {r.get("__name")} status={r.get("__status", {}).get("status")}')

kmd = active(load('zadanie_na_kmd'))
dop_tasks = [r for r in kmd if r.get('dop_zakaz_kmd_ref')]
obj_dop_tasks = []
for r in dop_tasks:
    ids = r.get('id_proekta') or []
    if isinstance(ids, str):
        ids = [ids]
    if oid in ids:
        obj_dop_tasks.append(r)
print(f'\nЗадания КМД с dop_zakaz_kmd_ref: {len(obj_dop_tasks)}')
for r in obj_dop_tasks[:10]:
    print(f'  {r.get("__name")} status={r.get("__status", {}).get("status")} ref={r.get("dop_zakaz_kmd_ref")}')
