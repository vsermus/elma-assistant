import urllib.request, json, os, sqlite3
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('OLLAMA_API_KEY')

# Берём 3 реальных диалога
c = sqlite3.connect('bot/chat_history.db')
rows = c.execute('SELECT role, text FROM messages ORDER BY id LIMIT 30').fetchall()
c.close()

pairs = []
for i in range(len(rows) - 1):
    if rows[i][0] == 'user' and rows[i+1][0] == 'assistant':
        pairs.append({'question': rows[i][1], 'answer': rows[i+1][1]})
    if len(pairs) == 3:
        break

print(f'Пар: {len(pairs)}')

dialogs = ''
for i, p in enumerate(pairs, 1):
    dialogs += f'[{i}] Вопрос: {p["question"][:150]}\nОтвет: {p["answer"][:200]}\n\n'

prompt = (
    f'Оцени {len(pairs)} диалога бота.\n'
    'Верни JSON-массив:\n'
    '[{"quality":1-5,"issue":"проблема или null","fix":"исправление или null","category":"тема"},...]\n\n'
    + dialogs +
    f'Ровно {len(pairs)} объекта. Только JSON.'
)

print('Длина промпта:', len(prompt), 'символов')

payload = json.dumps({
    'model': 'gemma3:27b',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 300,
    'temperature': 0
}).encode('utf-8')

req = urllib.request.Request(
    'https://ollama.com/v1/chat/completions',
    data=payload,
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=30) as r:
    resp = json.loads(r.read())
    content = resp['choices'][0]['message']['content']
    finish = resp['choices'][0].get('finish_reason')
    print(f'finish={finish}, длина ответа={len(content)}')
    print('Ответ (raw):', repr(content[:800]))

    # Парсинг
    start, end = content.find('['), content.rfind(']') + 1
    if start >= 0 and end > start:
        try:
            items = json.loads(content[start:end])
            print(f'\nJSON OK, элементов: {len(items)}')
            for item in items:
                print(' ', item)
        except Exception as e:
            print('Ошибка парсинга:', e)
    else:
        print('JSON-массив не найден')
