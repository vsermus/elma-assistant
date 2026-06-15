import os
import sys
import json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.dirname(__file__))
from core.data_provider import DataProvider
from core.aggregator import build_context_v2 as build_context
from core import claude_client

app = Flask(__name__)

with open(os.path.join(os.path.dirname(__file__), 'config', 'config.json'), 'r', encoding='utf-8') as f:
    config = json.load(f)

data_provider = DataProvider(config)

KMD_STATUSES = {1:'Назначено', 2:'В работе', 3:'Выполнено', 4:'Прервано', 5:'Ожидание снабжения', 6:'Снабжается'}


def load_entity(eid):
    try:
        return data_provider.load_entity(eid)
    except:
        return None


def load_spravochnik():
    return load_entity('spravochnik_id')


def build_object_map():
    sp = load_spravochnik()
    if not sp:
        return {}
    m = {}
    for item in sp:
        oid = item.get('__id')
        name = item.get('__name', '') or ''
        itog = item.get('itogovyi_id', '') or ''
        m[oid] = f'{itog} - {name}' if itog else name
    return m


def load_users_map():
    users = load_entity('users')
    if not users:
        return {}
    return {u.get('__id'): u.get('__name', u.get('fullname', '?')) for u in users}


def extract_ids(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def handle_kmd_query(query, obj_map):
    items = load_entity('zadanie_na_kmd')
    if not items:
        return 'Нет данных по заданиям КМД. Загрузи через load.'

    query_lower = query.lower()
    users_map = load_users_map()

    if any(w in query_lower for w in ['конструктор', 'исполнител', 'фамили', 'сотрудник', 'кто дела']):
        by_constructor = {}
        for item in items:
            pids = extract_ids(item.get('participants', []))
            for pid in pids:
                by_constructor.setdefault(pid, []).append(item)
        lines = [f'Задания КМД по конструкторам ({len(by_constructor)} человек):', '']
        for pid, tasks in sorted(by_constructor.items(), key=lambda x: -len(x[1])):
            name = users_map.get(pid, pid[:8])
            by_s = {}
            for t in tasks:
                s = t.get('__status', {}).get('status', 0)
                by_s[s] = by_s.get(s, 0) + 1
            parts = [f'{KMD_STATUSES.get(sid, str(sid))}:{cnt}' for sid, cnt in sorted(by_s.items())]
            lines.append(f'  {name} — {len(tasks)} заданий | {" | ".join(parts)}')
        return '\n'.join(lines)

    if any(w in query_lower for w in ['дата', 'startat', 'endat', 'когда', 'период', 'график']):
        lines = ['Задания КМД по месяцам (дата начала):', '']
        by_month = {}
        for item in items:
            start = item.get('startAt', '') or ''
            month = start[:7] if start else 'без даты'
            by_month.setdefault(month, []).append(item)
        for month in sorted(by_month.keys()):
            tasks = by_month[month]
            by_s = {}
            for t in tasks:
                s = t.get('__status', {}).get('status', 0)
                by_s[s] = by_s.get(s, 0) + 1
            parts = [f'{KMD_STATUSES.get(sid, str(sid))}:{cnt}' for sid, cnt in sorted(by_s.items())]
            lines.append(f'  {month} — {len(tasks)} заданий | {" | ".join(parts)}')
        lines.append('')
        lines.append(f'Всего: {len(items)} заданий')
        return '\n'.join(lines)

    if any(w in query_lower for w in ['статус', 'в работе', 'просрочен', 'сколько', 'все']):
        by_status = {}
        for item in items:
            s = item.get('__status', {}).get('status', 0)
            by_status.setdefault(s, []).append(item)

        lines = [f'Всего заданий КМД: {len(items)}', '']
        for sid in sorted(by_status.keys()):
            name = KMD_STATUSES.get(sid, f'Статус {sid}')
            cnt = len(by_status[sid])
            lines.append(f'  {name}: {cnt}')

        if 'в работе' in query_lower:
            in_work = by_status.get(2, [])
            lines.append('')
            lines.append(f'В работе ({len(in_work)}):')
            by_obj = {}
            for item in in_work:
                ids = extract_ids(item.get('id_proekta', []))
                for oid in ids:
                    by_obj.setdefault(oid, []).append(item)
            for oid, tasks in sorted(by_obj.items(), key=lambda x: -len(x[1])):
                obj_name = obj_map.get(oid, oid[:8] + '...')
                lines.append(f'  {obj_name} — {len(tasks)} заданий')

        if 'просрочен' in query_lower:
            overdue = []
            for item in items:
                s = item.get('__status', {}).get('status', 0)
                if s in (1, 2, 5, 6):
                    end = item.get('endAt')
                    if end:
                        overdue.append(item)
            lines.append('')
            lines.append(f'Просрочено (есть дата окончания, не выполнено): {len(overdue)}')
            if overdue:
                for item in overdue[:5]:
                    ids = extract_ids(item.get('id_proekta', []))
                    oid = ids[0] if ids else None
                    on = obj_map.get(oid, '') if oid else ''
                    lines.append(f'  {item.get("__name","?")} ({on})')

        return '\n'.join(lines)

    if any(w in query_lower for w in ['объект', 'itogovyi', 'по объект']):
        by_obj = {}
        for item in items:
            ids = extract_ids(item.get('id_proekta', []))
            for oid in ids:
                by_obj.setdefault(oid, []).append(item)

        lines = [f'Задания КМД по объектам ({len(by_obj)} объектов):', '']
        for oid, tasks in sorted(by_obj.items(), key=lambda x: -len(x[1])):
            on = obj_map.get(oid, oid[:8] + '...')
            lines.append(f'  {on} — {len(tasks)} заданий')
            by_s = {}
            for t in tasks:
                s = t.get('__status', {}).get('status', 0)
                by_s[s] = by_s.get(s, 0) + 1
            parts = [f'{KMD_STATUSES.get(sid, str(sid))}:{cnt}' for sid, cnt in sorted(by_s.items())]
            lines.append(f'    {" | ".join(parts)}')
        return '\n'.join(lines)

    return None


def handle_tender_query(query, obj_map):
    items = load_entity('tender')
    if not items:
        return 'Нет данных по тендерам.'
    query_lower = query.lower()

    if 'сколько' in query_lower or 'статус' in query_lower or 'все' in query_lower:
        by_status = {}
        for item in items:
            s = item.get('__status', {}).get('status', 0)
            by_status.setdefault(s, []).append(item)

        lines = [f'Всего тендеров: {len(items)}', '']
        for sid in sorted(by_status.keys()):
            lines.append(f'  Статус {sid}: {len(by_status[sid])}')

        if 'объект' in query_lower:
            lines.append('')
            by_obj = {}
            for item in items:
                ids = extract_ids(item.get('id_proekta_1', []))
                for oid in ids:
                    by_obj.setdefault(oid, []).append(item)
            for oid, tnds in sorted(by_obj.items(), key=lambda x: -len(x[1]))[:10]:
                on = obj_map.get(oid, oid[:8] + '...')
                lines.append(f'  {on} — {len(tnds)} тендеров')

        return '\n'.join(lines)

    if 'объект' in query_lower:
        by_obj = {}
        for item in items:
            ids = extract_ids(item.get('id_proekta_1', []))
            for oid in ids:
                by_obj.setdefault(oid, []).append(item)
        lines = [f'Тендеры по объектам ({len(by_obj)}):', '']
        for oid, tnds in sorted(by_obj.items(), key=lambda x: -len(x[1]))[:15]:
            on = obj_map.get(oid, oid[:8] + '...')
            lines.append(f'  {on} — {len(tnds)} тендеров')
        return '\n'.join(lines)

    return None


def process_query(user_query):
    obj_map = build_object_map()
    q = user_query.lower()

    answers = []

    if any(w in q for w in ['кмд', 'задание', 'витраж', 'ozm', 'знс', 'снабжение', 'карточк']):
        ans = handle_kmd_query(user_query, obj_map)
        if ans:
            answers.append(('КМД', ans))

    if any(w in q for w in ['тендер', 'работа', 'raboty', 'tender', 'заказчик', 'подряд']):
        ans = handle_tender_query(user_query, obj_map)
        if ans:
            answers.append(('Тендеры', ans))

    if not answers:
        answers.append(('Бот', 'Не понял запрос. Попробуй: "сколько заданий КМД в работе?", "статус тендеров", "объекты по КМД"'))

    result = []
    for label, text in answers:
        result.append(f'[{label}]\n{text}')

    return '\n\n'.join(result)


@app.route('/')
def index():
    return send_from_directory(os.path.join(app.root_path, 'web'), 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(os.path.join(app.root_path, 'web'), path)

@app.route('/api/query', methods=['POST'])
def query():
    req = request.get_json()
    user_query = req.get('query', '')
    if not user_query:
        return jsonify({'answer': 'Напиши запрос.'})
    answer = process_query(user_query)
    return jsonify({'answer': answer})

@app.route('/api/agents')
def list_agents():
    return jsonify({'agents': [
        {'id':'kmd','name':'КМД агент','enabled':True},
        {'id':'tender','name':'Тендерный агент','enabled':True},
        {'id':'excel','name':'Excel агент','enabled':False},
        {'id':'directory','name':'Справочный агент','enabled':True}
    ]})

@app.route('/api/data-status')
def data_status():
    ids = data_provider.get_all_loaded_entity_ids()
    ages = [data_provider.get_data_age_hours(eid) for eid in ids]
    ages = [a for a in ages if a is not None]
    return jsonify({
        'entities_count': len(ids),
        'entities': ids,
        'oldest_hours': max(ages) if ages else None,
        'newest_hours': min(ages) if ages else None
    })

@app.route('/api/refresh', methods=['POST'])
def refresh():
    data_provider.clear_cache()
    ids = data_provider.get_all_loaded_entity_ids()
    return jsonify({'updated': len(ids), 'entities': ids})


@app.route('/api/ai-query', methods=['POST'])
def ai_query():
    req = request.get_json()
    question = (req or {}).get('query', '').strip()
    if not question:
        return jsonify({'answer': 'Напиши вопрос.'})
    data_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    try:
        context = build_context(question, data_dir)
        answer = claude_client.ask(question, context)
    except Exception as e:
        answer = f'Ошибка: {e}'
    return jsonify({'answer': answer})

if __name__ == '__main__':
    print(f'ELMA Bot запущен: http://{config["server"]["host"]}:{config["server"]["port"]}')
    app.run(host=config['server']['host'], port=config['server']['port'], debug=config['server'].get('debug', False))
