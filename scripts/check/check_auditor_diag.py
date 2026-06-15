import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector')
import sys as _sys
_sys.path.insert(0, r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector')
from dotenv import load_dotenv
load_dotenv('.env')

token = os.getenv('ADMIN_BOT_TOKEN')
chat_id = os.getenv('ADMIN_CHAT_ID')
print('ADMIN_BOT_TOKEN:', 'задан' if token else 'НЕ ЗАДАН')
print('ADMIN_CHAT_ID:', chat_id if chat_id else 'НЕ ЗАДАН')

from bot.core.auditor import scan_recent, _get_last_audit_ts, send_report
print('Последний аудит:', _get_last_audit_ts())

problems = scan_recent()
print('Новых проблем с последнего аудита:', len(problems))
for p in problems:
    print(' ', p['type'], '|', p['question'][:60])

if not problems:
    print('\nНовых проблем нет — аудитор молчит, это нормально.')
    print('Чтобы увидеть все накопленные проблемы — пиши /failures в admin-бот.')
