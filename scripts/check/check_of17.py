import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))
from core.aggregator import _load_records, _active

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

sprav = _active(_load_records(os.path.join(DATA, 'spravochnik_id.json')))
obj = next((r for r in sprav if '230725' in str(r.get('itogovyi_id', ''))), None)
oid = obj['__id']

kv = _active(_load_records(os.path.join(DATA, 'kartochka_vitrazha_po_km.json')))
of17 = [r for r in kv if oid in (r.get('id_proekta') or []) and 'ОФ-17' in str(r.get('__name', ''))]
print(f'Карточек ОФ-17: {len(of17)}')
for r in of17:
    print(f'  name: {r.get("__name")}')
    print(f'  status: {r.get("__status", {}).get("status")}')
    print(f'  zadanie_na_kmd_2025: {r.get("zadanie_na_kmd_2025")}')
    print(f'  dop_kmd field: {r.get("dop_kmd")}')

kmd_ids = []
for r in of17:
    kmd_ids += r.get('zadanie_na_kmd_2025') or []
    kmd_ids += r.get('dop_kmd') or []

print(f'\nСвязанные задания КМД: {len(kmd_ids)} id')
kmd = _active(_load_records(os.path.join(DATA, 'zadanie_na_kmd.json')))
linked = [r for r in kmd if r.get('__id') in kmd_ids]
for r in linked:
    is_dop = bool(r.get('dop_zakaz_kmd_ref'))
    sid = r.get('__status', {}).get('status')
    print(f'  [{"ДОП" if is_dop else "ОСН"}] {r.get("__name")} status={sid}')

# ЗНС
zns_all = _active(_load_records(os.path.join(DATA, 'zns_po_kmd.json')))
linked_zns = [z for z in zns_all if any(k in (z.get('zadanie_na_kmd_2025') or []) for k in kmd_ids)]
print(f'\nЗНС по этим заданиям: {len(linked_zns)}')
for z in linked_zns:
    print(f'  {z.get("__name")} fill={z.get("vid_zapolneniya")} status={z.get("__status",{}).get("status")}')
