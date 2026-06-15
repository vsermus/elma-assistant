import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = 'bot/chat_history.db'
conn = sqlite3.connect(DB)

# Полные данные по проблемным failures
print('=== FAILURES (витражи + допы) ===')
rows = conn.execute(
    "SELECT id, type, ts, question, bot_answer FROM failures ORDER BY id"
).fetchall()
keywords = ['витраж', 'кмд', 'доп', '250725']
for r in rows:
    q = (r[3] or '').lower()
    if any(k in q for k in keywords):
        print(f'\n[{r[0]}] {r[1]} | {r[2]}')
        print(f'  Вопрос: {r[3]}')
        print(f'  Ответ бота: {r[4][:400]}')

print('\n\n=== ДИАЛОГ вокруг проблем (витражи + допы) ===')
# Найдём сообщения вокруг этих проблем из messages
msgs = conn.execute(
    "SELECT id, user_id, role, text, ts FROM messages ORDER BY id"
).fetchall()

# Найдём индексы сообщений с ключевыми словами
for i, (mid, uid, role, text, ts) in enumerate(msgs):
    t = (text or '').lower()
    if role == 'user' and any(k in t for k in keywords):
        start = max(0, i - 1)
        end = min(len(msgs), i + 4)
        print(f'\n--- контекст вокруг msg {mid} ({ts}) ---')
        for m in msgs[start:end]:
            print(f'  [{m[2]}] {m[4]}: {m[3][:200]}')

conn.close()
