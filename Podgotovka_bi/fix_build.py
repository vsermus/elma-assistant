with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\Podgotovka_bi\build_gantt_html.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function init() {', 700)
if idx > 0:
    end_marker = "'''"
    html_end = content.rfind(end_marker)
    before = content[:idx]
    after = content[html_end:]
    new_content = before + after
    with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\Podgotovka_bi\build_gantt_html.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Removed {html_end - idx} chars')
    print(f'New length: {len(new_content)}')
else:
    print('Second init not found')
