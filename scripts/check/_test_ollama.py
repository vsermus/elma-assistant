import sqlite3, urllib.request, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from dotenv import load_dotenv
load_dotenv()

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
for i, p in enumerate(pairs):
    print(f'  [{i+1}] {p["question"][:60]}')

dialogs = ''
for i, p in enumerate(pairs, 1):
    dialogs += f'[{i}] Вопрос: {p["question"][:200]}\nОтвет бота: {p["answer"][:300]}\n\n'

prompt = (
    f'Оцени качество ответов бота. Диалогов: {len(pairs)}.\n'
    'Верни JSON-массив:\n'
    '[{"quality":1-5,"issue":"проблема или null","fix":"что исправить или null","category":"тема"},...]\n\n'
    + dialogs +
    'quality: 5=отличный, 4=хороший, 3=удовлетворительный, 2=плохой, 1=не ответил.\n'
    f'Ровно {len(pairs)} объекта. Только JSON.'
)

api_key = os.getenv('OLLAMA_API_KEY')
payload = json.dumps({
    'model': 'deepseek-v4-flash',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 600,
    'temperature': 0
}).encode('utf-8')
req = urllib.request.Request(
    'https://ollama.com/v1/chat/completions',
    data=payload,
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=30) as r:
    resp = json.loads(r.read())
    text = resp['choices'][0]['message']['content']
    print('\n--- Полный сырой ответ ---')
    print(repr(text[:2000]))
    print('\n--- Парсинг ---')
    start, end = text.find('['), text.rfind(']') + 1
    if start >= 0 and end > start:
        try:
            items = json.loads(text[start:end])
            print('JSON OK, элементов:', len(items))
            for item in items:
                print(' ', item)
        except Exception as e:
            print('Ошибка парсинга:', e)
    else:
        print('JSON-массив не найден в ответе')
