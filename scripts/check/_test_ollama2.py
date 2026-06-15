import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('OLLAMA_API_KEY')

def test(model, prompt, max_tokens=200):
    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://ollama.com/v1/chat/completions',
        data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            content = resp['choices'][0]['message']['content']
            finish = resp['choices'][0].get('finish_reason')
            print(f'[{model}] finish={finish} len={len(content)}')
            print(repr(content[:500]))
    except Exception as e:
        print(f'[{model}] ERROR: {e}')

print('=== deepseek-v4-flash ===')
test('deepseek-v4-flash', 'Say OK')

print('\n=== ministral-3:8b ===')
test('ministral-3:8b', 'Say OK')

print('\n=== gemma3:4b ===')
test('gemma3:4b', 'Say OK')
