with open('dashboards/otchet_po_tenderam_v2/otchet_po_tenderam_v2.html', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    'tables-grid',
    'allTypeTable',
    'allTypeTableBody',
    'allTypeSummaryCount',
    'const totalAvg',
    '</html>'
]
for c in checks:
    found = c in content
    status = "OK" if found else "MISSING"
    print(f'  {c}: {status}')
print(f'Total size: {len(content)} bytes')
