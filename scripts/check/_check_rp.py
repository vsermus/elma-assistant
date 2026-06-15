import json, urllib.request, urllib.parse
TOKEN = '2ad06f66-6ecc-42b3-9bf4-1ef21eabb371'
params = urllib.parse.urlencode({'query': json.dumps({'size': 10000})})
req = urllib.request.Request(
    'https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/tender/raboty_po_tenderu_1/list?' + params,
    headers={'Authorization': f'Bearer {TOKEN}'})
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode('utf-8'))
tenders = data['result']['result']

rp_with_2026 = 0
rp_total = 0
for t in tenders:
    created = t.get('__createdAt','')
    rp = t.get('rukovoditel_proekta')
    has_rp = rp is not None and ((isinstance(rp,list) and len(rp) > 0 and any(rp))
                                  or (isinstance(rp,str) and rp.strip()))
    if has_rp:
        rp_total += 1
        if created and created.startswith('2026'):
            rp_with_2026 += 1
            if rp_with_2026 <= 3:
                tid = t.get('__id','')[:12]
                print(f'SAMPLE: id={tid} rp={rp}')

print(f'Total tenders with RP across all years: {rp_total}')
print(f'2026 tenders with RP: {rp_with_2026}')

# Also check all 2026 records
count_2026 = 0
for t in tenders:
    created = t.get('__createdAt','')
    if created and created.startswith('2026'):
        count_2026 += 1
        rp = t.get('rukovoditel_proekta')
        if rp:
            pass
print(f'Total 2026 tenders: {count_2026}')
