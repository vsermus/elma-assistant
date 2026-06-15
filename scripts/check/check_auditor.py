import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = 'bot/chat_history.db'
conn = sqlite3.connect(DB)

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Таблицы:', [t[0] for t in tables])

try:
    row = conn.execute("SELECT value FROM meta WHERE key='last_audit_ts'").fetchone()
    print('Последний аудит:', row[0] if row else 'нет данных')
except Exception as e:
    print('meta error:', e)

try:
    count = conn.execute('SELECT COUNT(*) FROM failures').fetchone()[0]
    print('Всего проблем в failures:', count)
    rows = conn.execute(
        'SELECT id, type, ts, category, question FROM failures ORDER BY id DESC LIMIT 20'
    ).fetchall()
    for r in rows:
        print(f'  [{r[0]}] {r[1]} | {r[2]} | кат: {r[3]} | {r[4][:80]}')
except Exception as e:
    print('failures error:', e)

try:
    msgs = conn.execute(
        "SELECT COUNT(*) FROM messages"
    ).fetchone()[0]
    print('Всего сообщений в messages:', msgs)
    last = conn.execute(
        "SELECT role, ts, text FROM messages ORDER BY id DESC LIMIT 5"
    ).fetchall()
    print('Последние сообщения:')
    for r in last:
        print(f'  [{r[0]}] {r[1]} | {r[2][:80]}')
except Exception as e:
    print('messages error:', e)

conn.close()
