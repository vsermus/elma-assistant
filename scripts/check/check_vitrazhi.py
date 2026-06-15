import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))
from core.aggregator import _load_records, _active

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
query = sys.argv[1] if len(sys.argv) > 1 else '230725'

sprav = _active(_load_records(os.path.join(DATA, 'spravochnik_id.json')))
obj = next((r for r in sprav if query in str(r.get('itogovyi_id', ''))), None)
if not obj:
    print('объект не найден'); sys.exit()

oid = obj['__id']
print(f'Объект: {obj.get("itogovyi_id")} id={oid}')

kv = _active(_load_records(os.path.join(DATA, 'kartochka_vitrazha_po_km.json')))
matched = [r for r in kv if oid in (r.get('id_proekta') or [])]
print(f'Карточек витражей: {len(matched)}')
print('Первые 15:')
for r in matched[:15]:
    name = r.get('__name', '')
    korpus = r.get('korpus', '')
    sekc = r.get('sekciya') or r.get('sections', '')
    sq = r.get('ploshad_po_km_m2') or r.get('ploshad_m2', '')
    print(f'  name={name!r} | korpus={korpus!r} | sekc={sekc!r} | sq={sq}')
