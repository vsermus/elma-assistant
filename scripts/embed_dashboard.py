import json, os

with open('data/tender_dashboard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

data_json = json.dumps(data, ensure_ascii=False)

output_file = 'dashboards/тендеры_по_типам_работ.html'
template_file = 'dashboards/тендеры_по_типам_работ.template.html'

if os.path.exists(template_file):
    with open(template_file, 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('%DATA%', data_json)
    print('Used template file')
else:
    with open(output_file, 'r', encoding='utf-8') as f:
        html = f.read()
    idx = html.find('const DATA = ')
    if idx >= 0:
        start = idx + len('const DATA = ')
        depth = 0
        end = start
        for i in range(start, len(html)):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        old_len = end - start
        new_len = len(data_json)
        html = html[:start] + data_json + html[end:]
        print(f'Replaced: old_len={old_len}, new_len={new_len}')
    else:
        print('ERROR: const DATA = not found')
        exit(1)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

new_size = os.path.getsize(output_file)
print(f'Output file size: {new_size}')
print(f'Data keys: {list(data.keys())}')
sts = data.get('statuses', 'NONE')
print(f'Statuses: {sts}')
