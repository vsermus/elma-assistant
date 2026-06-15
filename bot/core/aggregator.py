"""
Агрегатор данных ELMA для передачи в Claude API.
Читает локальные JSON, фильтрует удалённые записи, строит компактные сводки.
"""

import json
import os
import re

_DOP_RE = re.compile(r'\bдоп')

KMD_STATUSES = {
    1: 'В работе', 2: 'В работе', 3: 'Выполнено',
    4: 'Прервано', 5: 'Ожидание снабжения', 6: 'Снабжается'
}

BEFORE_TENDER_STATUSES = {1: 'Новый', 2: 'В работе', 3: 'Завершён'}


def _zns_stage(r):
    """Определяет стадию ЗНС по бизнес-логике (по полям, не по статусу ELMA)."""
    if r.get('data_fakt_otgruzki'):
        return 'Отгружено'
    if r.get('fakt_data_gotovnosti'):
        return 'Готово на складе'
    if r.get('data_razmesheniya_u_postavshika') or r.get('nomer_scheta'):
        return 'Размещено'
    if r.get('supplier_company'):
        return 'Выбран поставщик'
    if r.get('zns_1s'):
        return 'У МОС'
    if r.get('znz_1s') and not r.get('zns_1s'):
        return 'У РОС'
    sid = r.get('__status', {}).get('status', 0)
    if sid == 2:
        return 'В ПДО'
    return 'Новая'


def _load_records(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('statusItems', 'items'):
            val = data.get(key)
            if isinstance(val, list):
                return val
        result = data.get('result')
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            inner = result.get('result') or result.get('items')
            if isinstance(inner, list):
                return inner
    return []


def _active(records):
    return [r for r in records if not r.get('__deletedAt')]


def _short_name(full_name):
    parts = full_name.strip().split()
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
    if len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return full_name


def _fmt_date(raw: str) -> str:
    """Конвертирует ISO-дату (2026-04-17...) в ДД.ММ.ГГГГ."""
    s = (raw or '')[:10]
    if len(s) == 10 and s[4] == '-':
        return f'{s[8:10]}.{s[5:7]}.{s[:4]}'
    return s


def _vitrazh_short(name):
    """Извлекает короткое имя витража: 'к.11 с.3 ОФ-22' из полного __name."""
    for sep in (' к. ', ' к.'):
        idx = name.find(sep)
        if idx >= 0:
            short = name[idx:].strip()
            short = short.replace(' в. ', ' ').replace(' с. ', ' с.')
            return short
    return name[-40:]


def _build_maps(data_dir):
    sprav = _active(_load_records(os.path.join(data_dir, 'spravochnik_id.json')))
    obj_map = {}
    obj_details = {}
    for r in sprav:
        oid = r.get('__id')
        name = r.get('__name', '')
        itog = r.get('itogovyi_id', '') or ''
        obj_map[oid] = f"{itog} {name}".strip() if itog else name
        obj_details[oid] = {
            'rp': r.get('rukovoditel_proekta') or [],
            'rsd': r.get('rukovoditel_stroitelnoi_direkcii') or [],
            'address': r.get('stroitelnyi_adres', ''),
            'metrazh': r.get('metrazh'),
        }

    users = _active(_load_records(os.path.join(data_dir, 'users.json')))
    users_map = {u['__id']: _short_name(u.get('__name') or u.get('fullname') or '') for u in users if u.get('__id')}

    companies = _active(_load_records(os.path.join(data_dir, '_companies.json')))
    comp_map = {c['__id']: c.get('__name', '') for c in companies if c.get('__id')}

    return obj_map, users_map, comp_map, obj_details


def _load_status_map(path):
    items = _load_records(path)
    result = {}
    for s in items:
        sid = s.get('id') or s.get('__id')
        sname = s.get('name') or s.get('__name') or str(sid)
        if sid:
            result[str(sid)] = sname
    return result


def _has_obj(r, fields, object_ids):
    """Проверяет, относится ли запись к одному из указанных объектов."""
    for field in fields:
        val = r.get(field)
        if not val:
            continue
        if isinstance(val, str) and val in object_ids:
            return True
        if isinstance(val, list) and any(v in object_ids for v in val):
            return True
    return False


def get_objects_by_ids(ids: list, data_dir: str):
    """Возвращает [(id, display_name)] для указанных ID объектов, в том же порядке."""
    sprav = _active(_load_records(os.path.join(data_dir, 'spravochnik_id.json')))
    id_set = set(ids)
    display_map = {}
    for r in sprav:
        oid = r.get('__id', '')
        if oid in id_set:
            itog = r.get('itogovyi_id', '') or ''
            name = r.get('__name', '')
            display_map[oid] = f"{itog} — {name}".strip(' —') if itog else name
    return [(oid, display_map.get(oid, oid[:20])) for oid in ids if oid in display_map]


def search_objects(query, data_dir):
    """Ищет объекты строительства по строке. Возвращает [(id, display_name), ...]."""
    sprav = _active(_load_records(os.path.join(data_dir, 'spravochnik_id.json')))
    q = query.lower().strip()
    exact, partial = [], []
    seen = set()
    for r in sprav:
        oid = r.get('__id', '')
        if oid in seen:
            continue
        itog = (r.get('itogovyi_id') or '').lower()
        name = (r.get('__name') or '').lower()
        display = f"{r.get('itogovyi_id', '')} — {r.get('__name', '')}".strip(' —')
        if q == itog:
            exact.append((oid, display))
            seen.add(oid)
        elif q in itog or q in name:
            partial.append((oid, display))
            seen.add(oid)
    return exact + partial


_VITRAZH_CODE_RE = re.compile(r'[А-ЯЁ]{1,3}-\d+')


def search_vitrazhi(code: str, data_dir: str):
    """Ищет карточки витражей по коду (напр. ОФ-17). Возвращает [(kv_id, name, [obj_ids]), ...]."""
    all_kv = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    code_lower = code.lower()
    results = []
    for kv in all_kv:
        name = (kv.get('__name') or '').lower()
        if code_lower in name:
            obj_ids = kv.get('id_proekta') or []
            if isinstance(obj_ids, str):
                obj_ids = [obj_ids]
            results.append((kv['__id'], kv.get('__name', ''), list(obj_ids)))
    return results


def aggregate_single_vitrazh(data_dir: str, vitrazh_code: str, object_ids=None) -> str:
    """Детальная информация по конкретному витражу: статус карточки + КМД + ЗНС."""
    obj_map, users_map, comp_map, _ = _build_maps(data_dir)
    status_map = _load_status_map(os.path.join(data_dir, 'statusy_kartochka_vitrazha.json'))

    all_kv = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    code_lower = vitrazh_code.lower()
    kv_records = [
        r for r in all_kv
        if code_lower in (r.get('__name') or '').lower()
        and (not object_ids or _has_obj(r, ['id_proekta', 'idp4s'], object_ids))
    ]
    if not kv_records:
        return f'Витраж {vitrazh_code} не найден в данных.'

    all_kmd_ids = set()
    for kv in kv_records:
        for kid in (kv.get('zadanie_na_kmd_2025') or []):
            all_kmd_ids.add(kid)
        for kid in (kv.get('dop_kmd') or []):
            all_kmd_ids.add(kid)

    all_kmd = _active(_load_records(os.path.join(data_dir, 'zadanie_na_kmd.json')))
    kmd_map = {r['__id']: r for r in all_kmd if r.get('__id') in all_kmd_ids}

    all_zns = _active(_load_records(os.path.join(data_dir, 'zns_po_kmd.json')))
    all_zns = [z for z in all_zns if z.get('__status', {}).get('status') != 11]
    kmd_to_zns: dict = {}
    for z in all_zns:
        for kid in (z.get('zadanie_na_kmd_2025') or []):
            if kid in all_kmd_ids:
                kmd_to_zns.setdefault(kid, []).append(z)

    lines = [f'=== Витраж {vitrazh_code} ===',
             '[Показать каждый ЗНС отдельной строкой с заполнением, стадией и датой — отгрузки / готовности на складе / плановой]']
    for kv in kv_records:
        name = kv.get('__name', '')
        short = _vitrazh_short(name)
        sq = float(kv.get('ploshad_po_km_m2') or 0)
        sid = str(kv.get('__status', {}).get('status', 0))
        kv_status = status_map.get(sid, f'Статус {sid}')
        sq_str = f', {sq:,.1f} м²' if sq else ''

        obj_ids_r = kv.get('id_proekta') or []
        if isinstance(obj_ids_r, str):
            obj_ids_r = [obj_ids_r]
        obj_name = obj_map.get(obj_ids_r[0], '') if obj_ids_r else ''
        obj_str = f' ({obj_name})' if obj_name else ''

        lines.append(f'\n{short}{obj_str}{sq_str} — {kv_status}')

        kmd_ids_for_kv = (kv.get('zadanie_na_kmd_2025') or []) + (kv.get('dop_kmd') or [])
        for kid in kmd_ids_for_kv:
            kmd = kmd_map.get(kid)
            if not kmd:
                continue
            is_dop = bool(kmd.get('dop_zakaz_kmd_ref'))
            ksid = kmd.get('__status', {}).get('status', 0)
            kstatus = KMD_STATUSES.get(ksid, f'Статус {ksid}')
            label = 'ДОП КМД' if is_dop else 'КМД'
            rop = kmd.get('rop_date_original', '')
            rop_str = f', план {_fmt_date(rop)}' if rop else ''
            fakt = kmd.get('fakt_konec_kmd', '')
            fakt_str = f', факт {_fmt_date(fakt)}' if fakt else ''
            lines.append(f'  {label}: {kstatus}{rop_str}{fakt_str}')

            zns_list = kmd_to_zns.get(kid, [])
            if zns_list:
                lines.append(f'  ЗНС ({len(zns_list)}):')
                for z in zns_list:
                    fill = z.get('vid_zapolneniya') or 'Не указан'
                    khar = z.get('kharakteristika_zapolneniya') or ''
                    if khar and khar != 'нет данных':
                        fill = f'{fill} ({khar})'
                    stage = _zns_stage(z)
                    m = float(z.get('metrazh') or 0)
                    m_str = f', {m:,.1f} м²' if m else ''
                    sup_ids = z.get('supplier_company') or []
                    sup = comp_map.get(sup_ids[0], '') if sup_ids else ''
                    sup_str = f', {sup}' if sup else ''
                    if z.get('data_fakt_otgruzki'):
                        date_s = f', отгружено {_fmt_date(z["data_fakt_otgruzki"])}'
                    elif z.get('fakt_data_gotovnosti'):
                        date_s = f', готово на складе {_fmt_date(z["fakt_data_gotovnosti"])}'
                    elif z.get('plan_data_gotovnosti'):
                        date_s = f', план {_fmt_date(z["plan_data_gotovnosti"])}'
                    else:
                        date_s = ''
                    lines.append(f'    - {fill}: {stage}{m_str}{date_s}{sup_str}')
            elif ksid == 6:
                lines.append('  ЗНС: нет данных')

    return '\n'.join(lines)


def search_users(query, data_dir):
    """Ищет пользователей по имени. Возвращает [(id, display_name), ...]."""
    users = _active(_load_records(os.path.join(data_dir, 'users.json')))

    def _find(q):
        results, seen = [], set()
        for u in users:
            uid = u.get('__id', '')
            if uid in seen:
                continue
            name = (u.get('__name') or u.get('fullname') or '').lower()
            if q in name:
                display = u.get('__name') or u.get('fullname') or ''
                results.append((uid, display))
                seen.add(uid)
        return results

    q = query.lower().strip()
    results = _find(q)
    # Фолбэк для родительного падежа: "Иванова" → "Иванов"
    if not results and len(q) > 4 and q.endswith('а'):
        results = _find(q[:-1])
    elif results and len(q) > 4 and q.endswith('а'):
        # "Ивашечкина" нашла Анастасию — но это ещё и падеж от "Ивашечкин".
        # Добавляем только тех, у кого базовая форма совпадает с началом фамилии (первое слово),
        # чтобы не подтягивать людей с похожим отчеством (напр. "Павлович" при поиске "Павлова").
        existing_ids = {uid for uid, _ in results}
        base_q = q[:-1]
        for uid, name in _find(base_q):
            if uid not in existing_ids:
                surname = name.lower().split()[0] if name else ''
                if surname.startswith(base_q):
                    results.append((uid, name))
    return results


def _fmt_by_group(data, limit=15):
    lines = []
    sorted_items = sorted(data.items(), key=lambda x: -(sum(x[1].values()) if isinstance(x[1], dict) else x[1]))
    for k, v in sorted_items[:limit]:
        if isinstance(v, dict):
            parts = ', '.join(f"{sk}: {sv}" for sk, sv in sorted(v.items(), key=lambda x: -x[1]))
            lines.append(f"  {k}: {parts}")
        else:
            lines.append(f"  {k}: {v}")
    if len(sorted_items) > limit:
        lines.append(f"  ... и ещё {len(sorted_items) - limit}")
    return '\n'.join(lines)


def aggregate_kmd(data_dir, include_dynamics=False, object_ids=None, include_list=False):
    from datetime import datetime, timezone, timedelta
    all_records = _active(_load_records(os.path.join(data_dir, 'zadanie_na_kmd.json')))
    records = [r for r in all_records if not r.get('dop_zakaz_kmd_ref')]
    if object_ids:
        records = [r for r in records if _has_obj(r, ['id_proekta'], object_ids)]
    obj_map, users_map, _, _obj_details = _build_maps(data_dir)
    now = datetime.now(timezone.utc)
    days_30 = now - timedelta(days=30)

    # Метраж задания = сумма ploshad_po_km_m2 связанных карточек витражей
    kv_records = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    kmd_sq_map = {}
    kmd_to_kv = {}
    for kv in kv_records:
        sq = float(kv.get('ploshad_po_km_m2') or 0)
        for kid in (kv.get('zadanie_na_kmd_2025') or []):
            kmd_sq_map[kid] = kmd_sq_map.get(kid, 0) + sq
            kmd_to_kv.setdefault(kid, []).append(kv)

    by_status = {}
    by_status_sq = {}
    by_obj = {}
    by_obj_sq = {}
    active_by_obj = {}
    active_by_obj_sq = {}
    by_created_month = {}
    active_by_user = {}
    active_sq_by_user = {}
    overdue = []
    waiting_supply = []
    waiting_supply_by_year = {}
    waiting_supply_by_month = {}
    to_supply_30d = []
    active_list = []  # для include_list

    for r in records:
        sid = r.get('__status', {}).get('status', 0)
        sname = 'В работе' if sid in (1, 2) else KMD_STATUSES.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        rid = r.get('__id', '')
        sq = kmd_sq_map.get(rid, 0)
        by_status_sq[sname] = by_status_sq.get(sname, 0) + sq

        obj_ids = r.get('id_proekta') or []
        if isinstance(obj_ids, str):
            obj_ids = [obj_ids]
        obj_name = obj_map.get(obj_ids[0], 'Неизвестный объект') if obj_ids else 'Неизвестный объект'

        if obj_name not in by_obj:
            by_obj[obj_name] = {}
        by_obj[obj_name][sname] = by_obj[obj_name].get(sname, 0) + 1
        by_obj_sq[obj_name] = by_obj_sq.get(obj_name, 0) + sq

        constructor = None
        for pid in (r.get('participants') or []):
            constructor = users_map.get(pid, pid[:8] if pid else '?')

        if include_dynamics:
            if sid == 3:  # Выполнено — берём дату смены статуса
                done_month = (r.get('__statusChangedAt') or '')[:7]
                if done_month:
                    by_created_month[done_month] = by_created_month.get(done_month, 0) + 1

        # Активные (статус 1 или 2)
        if sid in (1, 2):
            if constructor:
                active_by_user[constructor] = active_by_user.get(constructor, 0) + 1
                active_sq_by_user[constructor] = active_sq_by_user.get(constructor, 0) + sq
            else:
                active_by_user['[без конструктора]'] = active_by_user.get('[без конструктора]', 0) + 1
                active_sq_by_user['[без конструктора]'] = active_sq_by_user.get('[без конструктора]', 0) + sq
            active_by_obj[obj_name] = active_by_obj.get(obj_name, 0) + 1
            active_by_obj_sq[obj_name] = active_by_obj_sq.get(obj_name, 0) + sq

            if include_list:
                kvs = kmd_to_kv.get(rid, [])
                korpusa = sorted(set(kv.get('korpus') or '' for kv in kvs if kv.get('korpus')))
                sektsii = sorted(set(
                    str(kv.get('sekciya') or kv.get('sections') or '') for kv in kvs
                    if kv.get('sekciya') or kv.get('sections')
                ))
                rop_raw_l = r.get('rop_date_original', '')
                active_list.append({
                    'obj': obj_name,
                    'korpus': ', '.join(korpusa),
                    'sektsii': ', '.join(sektsii),
                    'constructor': constructor or '—',
                    'sq': sq,
                    'rop': rop_raw_l[:10] if rop_raw_l else '',
                })

            # Просроченные: rop_date_original < сегодня
            rop_raw = r.get('rop_date_original')
            if rop_raw:
                try:
                    rop_dt = datetime.fromisoformat(rop_raw.replace('Z', '+00:00'))
                    if rop_dt < now:
                        overdue.append({
                            'name': r.get('__name', ''),
                            'obj': obj_name,
                            'rop': rop_raw[:10],
                            'days': (now - rop_dt).days,
                            'constructor': constructor or '?',
                            'sq': sq,
                        })
                except (ValueError, TypeError):
                    pass

        # Ожидание снабжения (статус 5)
        if sid == 5:
            changed_raw = r.get('__statusChangedAt')
            days_wait = None
            if changed_raw:
                try:
                    changed_dt = datetime.fromisoformat(changed_raw.replace('Z', '+00:00'))
                    days_wait = (now - changed_dt).days
                    year = str(changed_dt.year)
                    waiting_supply_by_year[year] = waiting_supply_by_year.get(year, 0) + 1
                    month = changed_dt.strftime('%Y-%m')
                    waiting_supply_by_month[month] = waiting_supply_by_month.get(month, 0) + 1
                except (ValueError, TypeError):
                    pass
            waiting_supply.append({
                'name': r.get('__name', ''),
                'obj': obj_name,
                'constructor': constructor or '?',
                'days': days_wait,
                'sq': sq,
            })

        # Передано в снабжение за 30 дней (статус 6)
        if sid == 6:
            changed_raw = r.get('__statusChangedAt')
            if changed_raw:
                try:
                    changed_dt = datetime.fromisoformat(changed_raw.replace('Z', '+00:00'))
                    if changed_dt >= days_30:
                        to_supply_30d.append({
                            'name': r.get('__name', ''),
                            'obj': obj_name,
                            'date': changed_raw[:10],
                            'sq': sq,
                        })
                except (ValueError, TypeError):
                    pass

    total_sq = sum(by_status_sq.values())
    total_sq_str = f", {total_sq:,.0f} м²" if total_sq else ""
    lines = [f"=== Задания на КМД (всего: {len(records)} заданий{total_sq_str}) ===", "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        sq = by_status_sq.get(s, 0)
        sq_str = f", {sq:,.0f} м²" if sq else ""
        lines.append(f"  {s}: {c} заданий{sq_str}")

    if active_by_user:
        lines.append("\nАктивные задания по конструкторам (В работе):")
        for uname, cnt in sorted(active_by_user.items(), key=lambda x: -x[1]):
            sq = active_sq_by_user.get(uname, 0)
            sq_str = f", {sq:,.0f} м²" if sq else ""
            lines.append(f"  {uname}: {cnt} заданий{sq_str}")

    if include_list and active_list:
        active_list.sort(key=lambda x: (x['obj'], x['korpus'], x['sektsii']))
        lines.append(f"\nСписок активных заданий (В работе, {len(active_list)}):")
        for it in active_list[:30]:
            parts = []
            if it['obj']:
                parts.append(it['obj'])
            if it['korpus']:
                parts.append(it['korpus'])
            if it['sektsii']:
                parts.append(f"с.{it['sektsii']}")
            label = ' '.join(parts) if parts else '—'
            sq_s = f", {it['sq']:,.0f} м²" if it['sq'] else ""
            cons_s = f" | {it['constructor']}" if it['constructor'] != '—' else ""
            rop_s = f", план {_fmt_date(it['rop'])}" if it['rop'] else ""
            lines.append(f"  {label}{sq_s}{cons_s}{rop_s}")
        if len(active_list) > 30:
            lines.append(f"  ... и ещё {len(active_list) - 30}")

    if active_by_obj:
        lines.append("\nВ работе по объектам:")
        for oname, cnt in sorted(active_by_obj.items(), key=lambda x: -x[1]):
            sq = active_by_obj_sq.get(oname, 0)
            sq_str = f", {sq:,.0f} м²" if sq else ""
            lines.append(f"  {oname}: {cnt} заданий{sq_str}")

    if overdue:
        overdue.sort(key=lambda x: -x['days'])
        lines.append(f"\nПросроченные активные задания (плановая дата прошла): {len(overdue)}")
        for o in overdue[:15]:
            sq_str = f", {o['sq']:,.0f} м²" if o['sq'] else ""
            lines.append(f"  {o['rop']} (+{o['days']}д) — {o['obj']} | {o['constructor']} | {o['name'][:40]}{sq_str}")
        if len(overdue) > 15:
            lines.append(f"  ... и ещё {len(overdue) - 15}")

    if waiting_supply:
        waiting_supply.sort(key=lambda x: -(x['days'] or 0))
        total_sq = sum(w['sq'] for w in waiting_supply)
        lines.append(f"\nОжидают отправки в снабжение: {len(waiting_supply)}, {total_sq:,.0f} м²")
        if waiting_supply_by_year:
            by_year_str = ', '.join(f"{y}: {c}" for y, c in sorted(waiting_supply_by_year.items()))
            lines.append(f"  По году: {by_year_str}")
        for w in waiting_supply[:5]:
            days_str = f"{w['days']}д" if w['days'] is not None else "?"
            sq_str = f", {w['sq']:,.0f} м²" if w['sq'] else ""
            lines.append(f"  {days_str} — {w['obj']} | {w['constructor']}{sq_str}")
        if len(waiting_supply) > 5:
            lines.append(f"  ... и ещё {len(waiting_supply) - 5}")

    if to_supply_30d:
        to_supply_30d.sort(key=lambda x: x['date'], reverse=True)
        total_sq_30 = sum(t['sq'] for t in to_supply_30d)
        lines.append(f"\nПередано в снабжение за 30 дней: {len(to_supply_30d)}, {total_sq_30:,.0f} м²")

    lines.append("\nПо объектам (топ-15):")
    sorted_objs = sorted(by_obj.items(), key=lambda x: -sum(x[1].values()))
    for obj_name, statuses in sorted_objs[:15]:
        total = sum(statuses.values())
        sq = by_obj_sq.get(obj_name, 0)
        sq_str = f", {sq:,.0f} м²" if sq else ""
        parts = ', '.join(f"{s}: {c}" for s, c in sorted(statuses.items(), key=lambda x: -x[1]))
        lines.append(f"  {obj_name}: {total} заданий{sq_str} ({parts})")
    if len(sorted_objs) > 15:
        lines.append(f"  ... и ещё {len(sorted_objs) - 15}")

    if include_dynamics and by_created_month:
        lines.append("\nВыполнено по месяцам:")
        for month in sorted(by_created_month):
            lines.append(f"  {month}: {by_created_month[month]}")

    return '\n'.join(lines)


def aggregate_tenders(data_dir):
    records = _active(_load_records(os.path.join(data_dir, 'tender.json')))
    obj_map, _, comp_map, _obj_details = _build_maps(data_dir)
    status_map = _load_status_map(os.path.join(data_dir, 'statusy_rabot_po_tenderam.json'))

    by_status, by_obj = {}, {}

    for r in records:
        sid = str(r.get('__status', {}).get('status', ''))
        sname = status_map.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        obj_ids = r.get('id_proekta_1') or []
        if isinstance(obj_ids, str):
            obj_ids = [obj_ids]
        for oid in obj_ids:
            oname = obj_map.get(oid, 'Неизвестный объект')
            by_obj[oname] = by_obj.get(oname, 0) + 1

    lines = [f"=== Тендеры (всего: {len(records)}) ===",
             "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  {s}: {c}")
    lines.append("\nПо объектам (топ-15):")
    lines.append(_fmt_by_group(by_obj, 15))
    return '\n'.join(lines)


def aggregate_works(data_dir):
    records = _active(_load_records(os.path.join(data_dir, 'raboty_po_tenderu.json')))
    status_map = _load_status_map(os.path.join(data_dir, 'statusy_rabot_po_tenderam.json'))

    by_status, by_type = {}, {}
    total_area = 0

    for r in records:
        sid = str(r.get('__status', {}).get('status', ''))
        sname = status_map.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        wtype = r.get('vid_rabot') or r.get('type_of_works') or 'Не указан'
        by_type[wtype] = by_type.get(wtype, 0) + 1

        try:
            total_area += float(r.get('ploshad') or r.get('area') or 0)
        except (ValueError, TypeError):
            pass

    lines = [f"=== Работы по тендерам (всего: {len(records)}, площадь: {total_area:,.0f} м²) ===",
             "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  {s}: {c}")
    lines.append("\nПо типам работ:")
    lines.append(_fmt_by_group(by_type, 10))
    return '\n'.join(lines)


def aggregate_orders_kmd(data_dir):
    records = _active(_load_records(os.path.join(data_dir, 'order_by_kmd.json')))
    obj_map, _, _, _obj_details = _build_maps(data_dir)
    status_map = _load_status_map(os.path.join(data_dir, 'statusy_order_by_kmd.json'))

    by_status, by_obj = {}, {}

    for r in records:
        sid = str(r.get('__status', {}).get('status', ''))
        sname = status_map.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        obj_ids = r.get('id_proekta') or []
        if isinstance(obj_ids, str):
            obj_ids = [obj_ids]
        for oid in obj_ids:
            oname = obj_map.get(oid, 'Неизвестный объект')
            by_obj[oname] = by_obj.get(oname, 0) + 1

    lines = [f"=== Заказы по КМД (всего: {len(records)}) ===",
             "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  {s}: {c}")
    lines.append("\nПо объектам (топ-10):")
    lines.append(_fmt_by_group(by_obj, 10))
    return '\n'.join(lines)


def aggregate_zns_po_kmd(data_dir, object_ids=None):
    all_records = _active(_load_records(os.path.join(data_dir, 'zns_po_kmd.json')))
    records = [r for r in all_records if r.get('__status', {}).get('status') != 11]
    if object_ids:
        records = [r for r in records if _has_obj(r, ['id_proekta', 'idp4s'], object_ids)]
    obj_map, users_map, comp_map, _obj_details = _build_maps(data_dir)

    by_stage, by_obj, by_supplier = {}, {}, {}
    total_metrazh = 0
    unique_invoices = set()
    total_sum = 0

    # {cname: {stage: {count, metrazh, fills: {fill: m2}, invoices: set((nomer, summa))}}}
    by_supplier_stages = {}

    for r in records:
        stage = _zns_stage(r)
        by_stage[stage] = by_stage.get(stage, 0) + 1

        obj_ids_r = r.get('id_proekta') or []
        if isinstance(obj_ids_r, str):
            obj_ids_r = [obj_ids_r]
        for oid in obj_ids_r:
            oname = obj_map.get(oid, 'Неизвестный объект')
            by_obj[oname] = by_obj.get(oname, 0) + 1

        try:
            metrazh_r = float(r.get('metrazh') or 0)
        except (ValueError, TypeError):
            metrazh_r = 0
        total_metrazh += metrazh_r

        fill = r.get('vid_zapolneniya') or 'Не указан'

        supplier_ids = r.get('supplier_company') or []
        sup_key = supplier_ids[0] if supplier_ids else ''
        nomer = str(r.get('nomer_scheta', '') or '')
        summa = r.get('summa_scheta', 0) or 0
        if nomer and sup_key:
            inv_key = (sup_key, nomer, summa)
            if inv_key not in unique_invoices:
                unique_invoices.add(inv_key)
                try:
                    total_sum += float(summa)
                except (ValueError, TypeError):
                    pass

        for cid in (r.get('supplier_company') or []):
            cname = comp_map.get(cid, '')
            if not cname:
                continue
            by_supplier[cname] = by_supplier.get(cname, 0) + 1
            if cname not in by_supplier_stages:
                by_supplier_stages[cname] = {}
            if stage not in by_supplier_stages[cname]:
                by_supplier_stages[cname][stage] = {'count': 0, 'metrazh': 0, 'fills': {}, 'invoices': set()}
            sd = by_supplier_stages[cname][stage]
            sd['count'] += 1
            sd['metrazh'] += metrazh_r
            sd['fills'][fill] = sd['fills'].get(fill, 0) + metrazh_r
            if nomer:
                sd['invoices'].add((nomer, summa))

    to_delete = len(all_records) - len(records) if not object_ids else 0
    lines = [f"=== ЗНС по КМД (всего: {len(records)}, метраж: {total_metrazh:,.0f} м²) ==="]
    if to_delete:
        lines.append(f"  (исключены «Подлежит удалению»: {to_delete})")
    lines.append("По стадиям:")
    stage_order = ['Новая', 'В ПДО', 'У РОС', 'У МОС', 'Выбран поставщик',
                   'Размещено', 'Готово на складе', 'Отгружено']
    for stage in stage_order:
        if stage in by_stage:
            lines.append(f"  {stage}: {by_stage[stage]}")
    for stage, cnt in sorted(by_stage.items()):
        if stage not in stage_order:
            lines.append(f"  {stage}: {cnt}")
    if total_sum > 0:
        lines.append(f"\nУникальных счетов: {len(unique_invoices)}, сумма: {total_sum:,.0f} ₽")
    lines.append("\nПо объектам (топ-15):")
    lines.append(_fmt_by_group(by_obj, 15))
    if by_supplier_stages:
        lines.append("\nПо поставщикам (топ-10):")
        stage_priority = ['Готово на складе', 'Размещено', 'Выбран поставщик',
                          'У МОС', 'У РОС', 'В ПДО', 'Новая', 'Отгружено']
        sorted_sup = sorted(by_supplier.items(), key=lambda x: -x[1])[:10]
        for cname, total in sorted_sup:
            stages = by_supplier_stages.get(cname, {})
            total_m = sum(sd['metrazh'] for sd in stages.values())
            m_str = f', {total_m:,.0f} м²' if total_m else ''
            lines.append(f"  {cname}: {total} ЗНС{m_str}")
            for s in stage_priority:
                if s not in stages:
                    continue
                sd = stages[s]
                sm = sd['metrazh']
                sm_str = f', {sm:,.0f} м²' if sm else ''
                # Сумма счетов по этой стадии (без дублей)
                stage_sum = sum(float(inv[1]) for inv in sd['invoices'] if inv[1])
                ss_str = f', {stage_sum:,.0f} ₽' if stage_sum else ''
                lines.append(f"    {s}: {sd['count']} ЗНС{sm_str}{ss_str}")
                # Заполнения топ-5
                fills = sorted(sd['fills'].items(), key=lambda x: -x[1])[:5]
                fill_parts = [f"{f}: {v:,.0f} м²" for f, v in fills if v > 0 and f != 'Не указан']
                if fill_parts:
                    lines.append(f"      Заполнения: {', '.join(fill_parts)}")
            # Стадии не из приоритетного списка
            for s, sd in stages.items():
                if s not in stage_priority:
                    lines.append(f"    {s}: {sd['count']} ЗНС")
    return '\n'.join(lines)


def aggregate_kartochka_vitrazha(data_dir, object_ids=None):
    all_records = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    records = all_records if not object_ids else [
        r for r in all_records if _has_obj(r, ['id_proekta', 'idp4s'], object_ids)
    ]
    obj_map, users_map, _, _obj_details = _build_maps(data_dir)
    status_map = _load_status_map(os.path.join(data_dir, 'statusy_kartochka_vitrazha.json'))

    by_status, by_obj, by_status_sq, by_obj_sq = {}, {}, {}, {}
    total_area = 0
    items = []

    for r in records:
        sid = str(r.get('__status', {}).get('status', 0))
        sname = status_map.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        try:
            sq = float(r.get('ploshad_po_km_m2') or 0)
            total_area += sq
        except (ValueError, TypeError):
            sq = 0

        by_status_sq[sname] = by_status_sq.get(sname, 0) + sq

        obj_ids = r.get('id_proekta') or []
        if isinstance(obj_ids, str):
            obj_ids = [obj_ids]
        for oid in obj_ids:
            oname = obj_map.get(oid, 'Неизвестный объект')
            by_obj[oname] = by_obj.get(oname, 0) + 1
            by_obj_sq[oname] = by_obj_sq.get(oname, 0) + sq

        cons_ids = r.get('constructor_kmd') or []
        if isinstance(cons_ids, str):
            cons_ids = [cons_ids]
        constructor = users_map.get(cons_ids[0], '') if cons_ids else ''

        plan_raw = (r.get('data_soglasovanaya_oeonchaniya_proektirovaniya')
                    or r.get('data_okonchaniya_proektirovaniya_vitrazha_po_km') or '')
        plan_date = plan_raw[:10] if plan_raw else ''

        items.append({
            'name': r.get('__name', ''),
            'status': sname,
            'sq': sq,
            'constructor': constructor,
            'plan_date': plan_date,
        })

    lines = [f"=== Карточки витражей по КМ (всего: {len(records)}, площадь: {total_area:,.0f} м²) ===",
             "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        sq = by_status_sq.get(s, 0)
        sq_str = f", {sq:,.0f} м²" if sq else ""
        lines.append(f"  {s}: {c} витражей{sq_str}")

    if object_ids:
        lines.append("\nСписок витражей по статусам:")
        by_s: dict = {}
        for it in items:
            by_s.setdefault(it['status'], []).append(it)
        for s, its in sorted(by_s.items(), key=lambda x: -len(x[1])):
            lines.append(f"\n{s} ({len(its)}):")
            for it in its[:12]:
                sq_str = f", {it['sq']:,.0f} м²" if it['sq'] else ""
                cons_str = f" | {it['constructor']}" if it['constructor'] else ""
                plan_str = f"{it['plan_date']} " if it.get('plan_date') else ""
                short = _vitrazh_short(it['name'])
                lines.append(f"  {plan_str}{short}{sq_str}{cons_str}")
            if len(its) > 12:
                lines.append(f"  ... и ещё {len(its) - 12}")
    else:
        lines.append("\nПо объектам (топ-15):")
        sorted_objs = sorted(by_obj.items(), key=lambda x: -x[1])
        for obj_name, cnt in sorted_objs[:15]:
            sq = by_obj_sq.get(obj_name, 0)
            sq_str = f", {sq:,.0f} м²" if sq else ""
            lines.append(f"  {obj_name}: {cnt} витражей{sq_str}")
        if len(sorted_objs) > 15:
            lines.append(f"  ... и ещё {len(sorted_objs) - 15}")

    return '\n'.join(lines)


def aggregate_ozm(data_dir):
    records = _active(_load_records(os.path.join(data_dir, 'ozm.json')))
    obj_map, users_map, _, _obj_details = _build_maps(data_dir)
    status_map = _load_status_map(os.path.join(data_dir, 'statusy_order_by_kmd.json'))

    by_status, by_obj = {}, {}
    total_metrazh = 0

    for r in records:
        sid = str(r.get('__status', {}).get('status', ''))
        sname = status_map.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        obj_ids = r.get('id_proekta_1') or r.get('idp4s') or []
        if isinstance(obj_ids, str):
            obj_ids = [obj_ids] if obj_ids else []
        for oid in obj_ids:
            oname = obj_map.get(oid, 'Неизвестный объект')
            by_obj[oname] = by_obj.get(oname, 0) + 1

        try:
            total_metrazh += float(r.get('metrazh') or 0)
        except (ValueError, TypeError):
            pass

    lines = [f"=== ОЗМ — Общий заказ материалов (всего: {len(records)}, метраж: {total_metrazh:,.0f} м²) ===",
             "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  {s}: {c}")
    lines.append("\nПо объектам (топ-15):")
    lines.append(_fmt_by_group(by_obj, 15))
    return '\n'.join(lines)


def aggregate_before_tender(data_dir):
    records = _active(_load_records(os.path.join(data_dir, 'before_tender.json')))
    _, users_map, comp_map, _obj_details = _build_maps(data_dir)

    by_status, by_rp, by_developer = {}, {}, {}
    total_metrazh = 0

    for r in records:
        sid = r.get('__status', {}).get('status', 0)
        sname = BEFORE_TENDER_STATUSES.get(sid, f'Статус {sid}')
        by_status[sname] = by_status.get(sname, 0) + 1

        for uid in (r.get('rp') or []):
            uname = users_map.get(uid, uid[:8] if uid else '?')
            by_rp[uname] = by_rp.get(uname, 0) + 1

        for cid in (r.get('developer') or []):
            cname = comp_map.get(cid, '')
            if cname:
                by_developer[cname] = by_developer.get(cname, 0) + 1

        try:
            total_metrazh += float(r.get('metrazh') or 0)
        except (ValueError, TypeError):
            pass

    lines = [f"=== Предтендерная подготовка (всего: {len(records)}, метраж: {total_metrazh:,.0f} м²) ===",
             "По статусам:"]
    for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  {s}: {c}")
    if by_rp:
        lines.append("\nПо РП:")
        lines.append(_fmt_by_group(by_rp, 10))
    if by_developer:
        lines.append("\nПо застройщику:")
        lines.append(_fmt_by_group(by_developer, 10))
    return '\n'.join(lines)


def aggregate_dop_kmd(data_dir, object_ids=None):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    all_dop = _active(_load_records(os.path.join(data_dir, 'dop_kmd.json')))
    dop_records = all_dop if not object_ids else [
        r for r in all_dop if _has_obj(r, ['id_proekta', 'idp4s'], object_ids)
    ]
    dop_status_map = _load_status_map(os.path.join(data_dir, 'statusy_dop_kmd.json'))
    obj_map, users_map, _, _obj_details = _build_maps(data_dir)

    all_kmd = _active(_load_records(os.path.join(data_dir, 'zadanie_na_kmd.json')))
    dop_tasks = [r for r in all_kmd if r.get('dop_zakaz_kmd_ref')]

    kv_records = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    kmd_sq_map = {}
    for kv in kv_records:
        sq = float(kv.get('ploshad_po_km_m2') or 0)
        for kid in (kv.get('zadanie_na_kmd_2025') or []):
            kmd_sq_map[kid] = kmd_sq_map.get(kid, 0) + sq

    # Карта: dop_kmd.__id → задания КМД
    dop_to_tasks = {}
    for r in dop_tasks:
        for ref in (r.get('dop_zakaz_kmd_ref') or []):
            dop_to_tasks.setdefault(ref, []).append(r)

    # ЗНС по ДОП: через zadanie_na_kmd_2025 → priznak_dop_kmd
    all_zns = _active(_load_records(os.path.join(data_dir, 'zns_po_kmd.json')))
    dop_kmd_ids = {r['__id'] for r in dop_tasks}
    zns_status_map = _load_status_map(os.path.join(data_dir, 'statusy_zns_po_kmd.json'))

    # Карта: zadanie_na_kmd.__id → список ЗНС
    kmd_to_zns: dict = {}
    for z in all_zns:
        for kid in (z.get('zadanie_na_kmd_2025') or []):
            if kid in dop_kmd_ids:
                kmd_to_zns.setdefault(kid, []).append(z)

    not_launched = []
    in_work = []        # В работе у конструктора (статус КМД 1,2)
    wait_supply = []    # Готово, ждёт снабжения (статус КМД 5)
    in_supply = []      # В снабжении (статус КМД 6 + ЗНС)
    total_area = 0

    for r in dop_records:
        did = r['__id']
        sid = r.get('__status', {}).get('status', 0)
        tasks = dop_to_tasks.get(did, [])

        obj_ids = r.get('id_proekta') or r.get('idp4s') or []
        if isinstance(obj_ids, str):
            obj_ids = [obj_ids] if obj_ids else []
        obj_name = obj_map.get(obj_ids[0], 'Неизвестный объект') if obj_ids else 'Неизвестный объект'

        area = 0
        try:
            area = float(r.get('ploshad_kmd') or 0)
        except (ValueError, TypeError):
            pass
        total_area += area

        days_waiting = None
        created_raw = r.get('__createdAt', '')
        if created_raw:
            try:
                created_dt = datetime.fromisoformat(created_raw.replace('Z', '+00:00'))
                days_waiting = (now - created_dt).days
            except (ValueError, TypeError):
                pass

        days_in_status = None
        changed_raw = r.get('__statusChangedAt', '')
        if changed_raw:
            try:
                changed_dt = datetime.fromisoformat(changed_raw.replace('Z', '+00:00'))
                days_in_status = (now - changed_dt).days
            except (ValueError, TypeError):
                pass

        item = {
            'name': r.get('__name', ''),
            'obj': obj_name,
            'area': area,
            'days_waiting': days_waiting,
            'days_in_status': days_in_status,
            'status': dop_status_map.get(str(sid), f'Статус {sid}'),
        }

        if not tasks or sid == 1:
            not_launched.append(item)
        else:
            for task in tasks:
                tsid = task.get('__status', {}).get('status', 0)
                sq = kmd_sq_map.get(task.get('__id', ''), 0)
                task_item = dict(item, sq=sq, task_name=task.get('__name', ''))

                if tsid in (1, 2):
                    in_work.append(task_item)
                elif tsid == 5:
                    wait_supply.append(task_item)
                elif tsid == 6:
                    zns_list = kmd_to_zns.get(task.get('__id', ''), [])
                    zns_by_status: dict = {}
                    for z in zns_list:
                        zsid = str(z.get('__status', {}).get('status', ''))
                        zsname = zns_status_map.get(zsid, f'Статус {zsid}')
                        zns_by_status[zsname] = zns_by_status.get(zsname, 0) + 1
                    in_supply.append(dict(task_item, zns=zns_by_status, zns_count=len(zns_list)))

    area_str = f", {total_area:,.0f} м²" if total_area > 0 else ""
    lines = [
        f"=== Дополнительные задания КМД (ДОП) — всего: {len(dop_records)}{area_str} ===",
        f"  Не запущены: {len(not_launched)}",
        f"  В работе у конструктора: {len(in_work)}",
        f"  Ждут снабжения: {len(wait_supply)}",
        f"  В снабжении: {len(in_supply)}",
    ]

    if not_launched:
        not_launched.sort(key=lambda x: -(x['days_waiting'] or 0))
        lines.append(f"\nНе запущены — ожидают передачи конструктору ({len(not_launched)}):")
        for e in not_launched[:15]:
            days_str = f"{e['days_waiting']}д" if e['days_waiting'] is not None else "?"
            status_days = f" ({e['days_in_status']}д в «{e['status']}»)" if e['days_in_status'] is not None else ""
            area_str2 = f", {e['area']:,.0f} м²" if e['area'] else ""
            lines.append(f"  {days_str} ожидания{status_days} — {e['obj']}{area_str2} | {e['name'][:40]}")
        if len(not_launched) > 15:
            lines.append(f"  ... и ещё {len(not_launched) - 15}")

    if in_work:
        in_work.sort(key=lambda x: -(x['days_waiting'] or 0))
        total_sq = sum(it['sq'] for it in in_work)
        sq_str = f", {total_sq:,.0f} м²" if total_sq else ""
        lines.append(f"\nВ работе у конструктора ({len(in_work)}{sq_str}):")
        for it in in_work[:15]:
            sq_str2 = f", {it['sq']:,.0f} м²" if it['sq'] else ""
            lines.append(f"  {it['obj']}{sq_str2} | {it['name'][:50]}")
        if len(in_work) > 15:
            lines.append(f"  ... и ещё {len(in_work) - 15}")

    if wait_supply:
        wait_supply.sort(key=lambda x: -(x['days_waiting'] or 0))
        total_sq = sum(it['sq'] for it in wait_supply)
        sq_str = f", {total_sq:,.0f} м²" if total_sq else ""
        lines.append(f"\nГотово, ждёт снабжения ({len(wait_supply)}{sq_str}):")
        for it in wait_supply[:15]:
            sq_str2 = f", {it['sq']:,.0f} м²" if it['sq'] else ""
            days_str = f"{it['days_waiting']}д" if it['days_waiting'] is not None else "?"
            lines.append(f"  {days_str} — {it['obj']}{sq_str2} | {it['name'][:50]}")
        if len(wait_supply) > 15:
            lines.append(f"  ... и ещё {len(wait_supply) - 15}")

    if in_supply:
        total_sq = sum(it['sq'] for it in in_supply)
        total_zns = sum(it['zns_count'] for it in in_supply)
        sq_str = f", {total_sq:,.0f} м²" if total_sq else ""
        lines.append(f"\nВ снабжении ({len(in_supply)}{sq_str}), ЗНС: {total_zns}:")
        all_zns_statuses: dict = {}
        for it in in_supply:
            for s, c in it['zns'].items():
                all_zns_statuses[s] = all_zns_statuses.get(s, 0) + c
        if all_zns_statuses:
            lines.append("  Статусы ЗНС: " + ", ".join(
                f"{s}: {c}" for s, c in sorted(all_zns_statuses.items(), key=lambda x: -x[1])
            ))
        for it in in_supply[:15]:
            sq_str2 = f", {it['sq']:,.0f} м²" if it['sq'] else ""
            zns_str = f" | ЗНС: {', '.join(f'{s}:{c}' for s,c in it['zns'].items())}" if it['zns'] else ""
            lines.append(f"  {it['obj']}{sq_str2} | {it['name'][:45]}{zns_str}")
        if len(in_supply) > 15:
            lines.append(f"  ... и ещё {len(in_supply) - 15}")

    # Сводка по объектам
    by_obj_summary: dict = {}
    for it in not_launched:
        by_obj_summary.setdefault(it['obj'], {'Не запущен': 0, 'В работе': 0, 'Ждёт снабжения': 0, 'В снабжении': 0})
        by_obj_summary[it['obj']]['Не запущен'] += 1
    for it in in_work:
        by_obj_summary.setdefault(it['obj'], {'Не запущен': 0, 'В работе': 0, 'Ждёт снабжения': 0, 'В снабжении': 0})
        by_obj_summary[it['obj']]['В работе'] += 1
    for it in wait_supply:
        by_obj_summary.setdefault(it['obj'], {'Не запущен': 0, 'В работе': 0, 'Ждёт снабжения': 0, 'В снабжении': 0})
        by_obj_summary[it['obj']]['Ждёт снабжения'] += 1
    for it in in_supply:
        by_obj_summary.setdefault(it['obj'], {'Не запущен': 0, 'В работе': 0, 'Ждёт снабжения': 0, 'В снабжении': 0})
        by_obj_summary[it['obj']]['В снабжении'] += 1

    if by_obj_summary:
        sorted_objs = sorted(by_obj_summary.items(), key=lambda x: -sum(x[1].values()))
        lines.append(f"\nПо объектам (всего {len(sorted_objs)}):")
        for obj_name, cats in sorted_objs:
            total = sum(cats.values())
            parts_str = ', '.join(f"{k}: {v}" for k, v in cats.items() if v > 0)
            lines.append(f"  {obj_name}: итого {total} ({parts_str})")

    return '\n'.join(lines)


def aggregate_user_objects(data_dir, user_id, users_map):
    """Объекты строительства, где пользователь — РП или РСД."""
    sprav = _active(_load_records(os.path.join(data_dir, 'spravochnik_id.json')))

    # Схлопываем дубли: ключ = (itogovyi_id, __name), берём запись с наибольшим заполнением
    seen: dict = {}
    for r in sprav:
        key = (r.get('itogovyi_id') or '', r.get('__name', ''))
        prev = seen.get(key)
        if prev is None or len([v for v in r.values() if v]) > len([v for v in prev.values() if v]):
            seen[key] = r

    as_rp, as_rsd = [], []
    for r in seen.values():
        rp_ids = r.get('rukovoditel_proekta') or []
        if isinstance(rp_ids, str):
            rp_ids = [rp_ids]
        rsd_ids = r.get('rukovoditel_stroitelnoi_direkcii') or []
        if isinstance(rsd_ids, str):
            rsd_ids = [rsd_ids]

        itog = r.get('itogovyi_id', '') or ''
        name = r.get('__name', '')
        display = f"{itog} — {name}".strip(' —') if itog else name
        metrazh = r.get('metrazh')
        sq_str = f", {float(metrazh):,.0f} м²" if metrazh else ""

        if user_id in rp_ids:
            as_rp.append(f"  {display}{sq_str}")
        if user_id in rsd_ids:
            as_rsd.append(f"  {display}{sq_str}")

    lines = []
    if as_rp:
        lines.append(f"Объекты как РП ({len(as_rp)}):")
        lines.extend(sorted(as_rp))
    if as_rsd:
        lines.append(f"Объекты как РСД ({len(as_rsd)}):")
        lines.extend(sorted(as_rsd))
    return lines


def aggregate_user_kmd(data_dir, user_id):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    all_records = _active(_load_records(os.path.join(data_dir, 'zadanie_na_kmd.json')))
    records = [r for r in all_records if not r.get('dop_zakaz_kmd_ref')
               and user_id in (r.get('participants') or [])]

    obj_map, users_map, _, _obj_details = _build_maps(data_dir)

    kv_records = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    kmd_sq_map = {}
    for kv in kv_records:
        sq = float(kv.get('ploshad_po_km_m2') or 0)
        for kid in (kv.get('zadanie_na_kmd_2025') or []):
            kmd_sq_map[kid] = kmd_sq_map.get(kid, 0) + sq

    by_status, by_status_sq, overdue = {}, {}, []

    for r in records:
        sid = r.get('__status', {}).get('status', 0)
        sname = 'В работе' if sid in (1, 2) else KMD_STATUSES.get(sid, f'Статус {sid}')
        rid = r.get('__id', '')
        sq = kmd_sq_map.get(rid, 0)
        by_status[sname] = by_status.get(sname, 0) + 1
        by_status_sq[sname] = by_status_sq.get(sname, 0) + sq

        if sid in (1, 2):
            rop_raw = r.get('rop_date_original')
            if rop_raw:
                try:
                    rop_dt = datetime.fromisoformat(rop_raw.replace('Z', '+00:00'))
                    if rop_dt < now:
                        obj_ids = r.get('id_proekta') or []
                        if isinstance(obj_ids, str):
                            obj_ids = [obj_ids]
                        obj_name = obj_map.get(obj_ids[0], 'Неизвестный объект') if obj_ids else 'Неизвестный объект'
                        overdue.append({
                            'name': r.get('__name', ''),
                            'obj': obj_name,
                            'rop': rop_raw[:10],
                            'days': (now - rop_dt).days,
                            'sq': sq,
                        })
                except (ValueError, TypeError):
                    pass

    user_name = users_map.get(user_id, '?')
    lines = [f"=== Сотрудник: {user_name} ==="]

    # Объекты как РП/РСД
    obj_lines = aggregate_user_objects(data_dir, user_id, users_map)
    if obj_lines:
        lines.append("")
        lines.extend(obj_lines)

    # Задания КМД как конструктор
    total_sq = sum(by_status_sq.values())
    sq_str = f", {total_sq:,.0f} м²" if total_sq else ""
    lines.append(f"\nЗадания КМД как конструктор (всего: {len(records)}{sq_str}):")
    if records:
        for s, c in sorted(by_status.items(), key=lambda x: -x[1]):
            sq = by_status_sq.get(s, 0)
            lines.append(f"  {s}: {c} заданий{f', {sq:,.0f} м²' if sq else ''}")
    else:
        lines.append("  нет заданий")

    if overdue:
        overdue.sort(key=lambda x: -x['days'])
        lines.append(f"\nПросроченные задания КМД: {len(overdue)}")
        for o in overdue[:10]:
            sq_str2 = f", {o['sq']:,.0f} м²" if o['sq'] else ""
            lines.append(f"  {o['rop']} (+{o['days']}д) — {o['obj']} | {o['name'][:40]}{sq_str2}")

    return '\n'.join(lines)


def aggregate_kmd_full(data_dir, object_ids=None, is_dop=False, include_vitrazhi=False):
    """Сквозной агрегатор: КМД → ЗНС по объекту. Центральная функция для вопросов по витражам."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    obj_map, users_map, comp_map, _ = _build_maps(data_dir)

    # Карточки витражей
    all_kv = _active(_load_records(os.path.join(data_dir, 'kartochka_vitrazha_po_km.json')))
    kv_records = [r for r in all_kv if _has_obj(r, ['id_proekta', 'idp4s'], object_ids)] if object_ids else all_kv

    # Карта: zadanie_na_kmd_id → список карточек витражей
    kmd_to_kv = {}
    for kv in kv_records:
        for kid in (kv.get('zadanie_na_kmd_2025') or []):
            kmd_to_kv.setdefault(kid, []).append(kv)

    # Задания КМД: фильтр ДОП
    all_kmd = _active(_load_records(os.path.join(data_dir, 'zadanie_na_kmd.json')))
    if is_dop:
        kmd_records = [r for r in all_kmd if r.get('dop_zakaz_kmd_ref')]
    else:
        kmd_records = [r for r in all_kmd if not r.get('dop_zakaz_kmd_ref')]

    # Фильтр по объекту: через карточки витражей или через id_proekta
    if object_ids:
        linked_ids = set(kmd_to_kv.keys())
        kmd_records = [r for r in kmd_records
                       if r.get('__id') in linked_ids or _has_obj(r, ['id_proekta'], object_ids)]

    # ЗНС: карта zadanie_na_kmd_id → список ЗНС
    all_zns = _active(_load_records(os.path.join(data_dir, 'zns_po_kmd.json')))
    all_zns = [z for z in all_zns if z.get('__status', {}).get('status') != 11]
    kmd_to_zns = {}
    for z in all_zns:
        for kid in (z.get('zadanie_na_kmd_2025') or []):
            kmd_to_zns.setdefault(kid, []).append(z)

    in_work, wait_supply, in_supply, done, interrupted = [], [], [], [], []
    total_sq = 0

    for r in kmd_records:
        sid = r.get('__status', {}).get('status', 0)
        rid = r.get('__id', '')
        kvs = kmd_to_kv.get(rid, [])
        sq = sum(float(kv.get('ploshad_po_km_m2') or 0) for kv in kvs)
        total_sq += sq

        obj_ids_r = r.get('id_proekta') or []
        if isinstance(obj_ids_r, str):
            obj_ids_r = [obj_ids_r]
        obj_name = obj_map.get(obj_ids_r[0], '') if obj_ids_r else ''

        korpusa = sorted(set(kv.get('korpus') or '' for kv in kvs if kv.get('korpus')))
        sektsii = sorted(set(
            str(kv.get('sekciya') or kv.get('sections') or '') for kv in kvs
            if kv.get('sekciya') or kv.get('sections')
        ))

        codes = []
        if include_vitrazhi:
            seen_codes = set()
            for kv in kvs:
                m = _VITRAZH_CODE_RE.search(kv.get('__name') or '')
                if m and m.group(0) not in seen_codes:
                    seen_codes.add(m.group(0))
                    codes.append(m.group(0))

        item = {
            'id': rid,
            'obj': obj_name,
            'korpus': ', '.join(korpusa),
            'sektsii': ', '.join(sektsii),
            'sq': sq,
            'vitrazhi': len(kvs),
            'codes': codes,
        }

        if sid in (1, 2):
            rop_raw = r.get('rop_date_original', '')
            rop_date = rop_raw[:10] if rop_raw else ''
            overdue = False
            if rop_raw:
                try:
                    overdue = datetime.fromisoformat(rop_raw.replace('Z', '+00:00')) < now
                except (ValueError, TypeError):
                    pass
            item.update({'rop_date': rop_date, 'overdue': overdue})
            in_work.append(item)
        elif sid == 5:
            wait_supply.append(item)
        elif sid == 6:
            zns_list = kmd_to_zns.get(rid, [])
            zns_rows = []
            for z in zns_list:
                sup_ids = z.get('supplier_company') or []
                supplier = comp_map.get(sup_ids[0], '') if sup_ids else ''
                zns_rows.append({
                    'fill': z.get('vid_zapolneniya') or 'Не указан',
                    'stage': _zns_stage(z),
                    'metrazh': z.get('metrazh', 0),
                    'plan': (z.get('plan_data_gotovnosti') or '')[:10],
                    'fakt': (z.get('fakt_data_gotovnosti') or '')[:10],
                    'otgr': (z.get('data_fakt_otgruzki') or '')[:10],
                    'supplier': supplier,
                })
            item['zns'] = zns_rows
            in_supply.append(item)
        elif sid == 3:
            done.append(item)
        elif sid == 4:
            interrupted.append(item)

    label = 'ДОП-задания на КМД' if is_dop else 'Задания на КМД'
    obj_label = ''
    if object_ids and len(object_ids) == 1:
        obj_label = f' / {obj_map.get(object_ids[0], "")}'
    total = len(kmd_records)
    sq_str = f', {total_sq:,.0f} м²' if total_sq else ''
    lines = [f'=== {label}{obj_label} (всего: {total}{sq_str}) ===',
             f'  В работе: {len(in_work)}  |  Ожидают ЗНС: {len(wait_supply)}  |  В снабжении: {len(in_supply)}  |  Выполнено: {len(done)}']
    if interrupted:
        lines.append(f'  Прервано: {len(interrupted)}')

    show_obj = not object_ids or len(object_ids) > 1

    def _fmt_item(it, show_obj):
        parts = []
        if show_obj and it['obj']:
            parts.append(it['obj'])
        if it['korpus']:
            parts.append(it['korpus'])
        if it['sektsii']:
            parts.append(f'с.{it["sektsii"]}')
        label = ' '.join(parts) if parts else '—'
        sq_s = f', {it["sq"]:,.0f} м²' if it['sq'] else ''
        codes = it.get('codes', [])
        if codes:
            shown = codes[:8]
            extra = len(codes) - 8
            tail = f' ...+{extra}' if extra > 0 else ''
            codes_s = f' [{", ".join(shown)}{tail}]'
        else:
            codes_s = ''
        return f'{label}{sq_s}{codes_s}'

    if in_work:
        in_work.sort(key=lambda x: (not x.get('overdue'), x.get('rop_date') or '9'))
        lines.append(f'\nВ работе у конструктора ({len(in_work)}):')
        for it in in_work[:20]:
            base = _fmt_item(it, show_obj)
            rop = f', план {it["rop_date"]}' if it.get('rop_date') else ''
            warn = ' ⚠ просрочено' if it.get('overdue') else ''
            lines.append(f'  {base}{rop}{warn}')
        if len(in_work) > 20:
            lines.append(f'  ... и ещё {len(in_work) - 20}')

    if wait_supply:
        lines.append(f'\nКМД готово, ЗНС ещё не созданы ({len(wait_supply)}):')
        for it in wait_supply[:20]:
            lines.append(f'  {_fmt_item(it, show_obj)}')
        if len(wait_supply) > 20:
            lines.append(f'  ... и ещё {len(wait_supply) - 20}')

    if in_supply:
        lines.append(f'\nВ снабжении ({len(in_supply)}):')
        for it in in_supply[:15]:
            lines.append(f'  {_fmt_item(it, show_obj)}:')
            for z in it['zns'][:10]:
                m = f', {float(z["metrazh"] or 0):,.1f} м²' if z.get('metrazh') else ''
                date_s = ''
                if z['otgr']:
                    date_s = f', отгружено {z["otgr"]}'
                elif z['fakt']:
                    date_s = f', готово {z["fakt"]}'
                elif z['plan']:
                    date_s = f', план {z["plan"]}'
                sup = f', {z["supplier"]}' if z.get('supplier') else ''
                lines.append(f'    - {z["fill"]}: {z["stage"]}{m}{date_s}{sup}')
            if len(it['zns']) > 10:
                lines.append(f'    ... и ещё {len(it["zns"]) - 10} ЗНС')
        if len(in_supply) > 15:
            lines.append(f'  ... и ещё {len(in_supply) - 15}')

    return '\n'.join(lines)


_DYNAMICS_KW = ['динамик', 'по месяц', 'по кварт', 'за месяц', 'за кварт', 'тренд', 'история выполнен']
_LIST_KW = ['какие', 'список', 'перечисли', 'все задани', 'покажи задани', 'выведи задани', 'выведите задани', 'все кмд', 'какие кмд']


def aggregate_object_info(data_dir: str, object_ids: list) -> str:
    sprav = _active(_load_records(os.path.join(data_dir, 'spravochnik_id.json')))
    users = _active(_load_records(os.path.join(data_dir, 'users.json')))
    users_map = {u['__id']: u.get('__name') or u.get('fullname') or '' for u in users if u.get('__id')}

    lines = []
    for r in sprav:
        if r.get('__id') not in object_ids:
            continue
        itog = r.get('itogovyi_id', '') or ''
        name = r.get('__name', '')
        display = f"{itog} {name}".strip() if itog else name
        lines.append(f"=== Объект: {display} ===")

        rp_ids = r.get('rukovoditel_proekta') or []
        if isinstance(rp_ids, str):
            rp_ids = [rp_ids]
        rp_names = [users_map.get(uid, uid[:8]) for uid in rp_ids if uid]
        lines.append(f"  Руководитель проекта (РП): {', '.join(rp_names) if rp_names else 'не указан'}")

        rsd_ids = r.get('rukovoditel_stroitelnoi_direkcii') or []
        if isinstance(rsd_ids, str):
            rsd_ids = [rsd_ids]
        rsd_names = [users_map.get(uid, uid[:8]) for uid in rsd_ids if uid]
        lines.append(f"  Руководитель строительной дирекции (РСД): {', '.join(rsd_names) if rsd_names else 'не указан'}")

        address = r.get('stroitelnyi_adres', '')
        if address:
            lines.append(f"  Адрес: {address}")
        metrazh = r.get('metrazh')
        if metrazh:
            lines.append(f"  Метраж: {float(metrazh):,.1f} м²")

    return '\n'.join(lines) if lines else ''


def _get_data_date(data_dir: str) -> str:
    log_path = os.path.join(data_dir, 'load_log.json')
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log = json.load(f)
            ts = log.get('_last_load', '')
            if ts:
                from datetime import datetime
                dt = datetime.fromisoformat(ts)
                return dt.strftime('%d.%m.%Y %H:%M')
        except Exception:
            pass
    return ''


def build_context_v2(question: str, data_dir: str, forced_categories=None, object_ids=None,
                     user_id=None, vitrazh_code: str | None = None) -> str:
    """Роутинг через AI (gemma3:27b). При наличии объекта — сквозной агрегатор КМД→ЗНС."""
    if user_id:
        return aggregate_user_kmd(data_dir, user_id)

    q = question.lower()
    include_dynamics = any(kw in q for kw in _DYNAMICS_KW)
    is_dop = bool(_DOP_RE.search(q))
    include_list = any(kw in q for kw in _LIST_KW)

    if forced_categories is not None:
        categories = forced_categories
    else:
        from core.claude_client import route_question
        try:
            categories = route_question(question)
        except Exception:
            categories = []

    parts = []

    _VITRAZH_KW = ['витраж', 'карточк', 'остеклен']

    # Если запрошен конкретный витраж — показываем только его (КМД + ЗНС)
    if vitrazh_code:
        obj_info = aggregate_object_info(data_dir, object_ids) if object_ids else ''
        if obj_info:
            parts.append(obj_info)
        parts.append(aggregate_single_vitrazh(data_dir, vitrazh_code, object_ids=object_ids))
        data_date = _get_data_date(data_dir)
        header = f"Данные актуальны на: {data_date}\n\n" if data_date else ''
        return header + '\n\n'.join(parts)

    if object_ids:
        # Для вопросов по конкретному объекту — сквозной агрегатор КМД→ЗНС
        obj_info = aggregate_object_info(data_dir, object_ids)
        if obj_info:
            parts.append(obj_info)
        include_vitrazhi = any(kw in q for kw in _VITRAZH_KW)
        parts.append(aggregate_kmd_full(data_dir, object_ids=object_ids, is_dop=is_dop, include_vitrazhi=include_vitrazhi))
        # Если спросили про витражи — добавляем карточки витражей по объекту
        if any(kw in q for kw in _VITRAZH_KW):
            parts.append(aggregate_kartochka_vitrazha(data_dir, object_ids=object_ids))
        # Если явно спросили только про ЗНС (без КМД) — добавляем отдельную сводку по ЗНС
        if 'zns_po_kmd' in categories and 'zadanie_na_kmd' not in categories:
            parts.append(aggregate_zns_po_kmd(data_dir, object_ids=object_ids))
    else:
        for cat in categories:
            if cat == 'zadanie_na_kmd':
                parts.append(aggregate_kmd(data_dir, include_dynamics=include_dynamics, include_list=include_list))
            elif cat == 'dop_kmd':
                parts.append(aggregate_dop_kmd(data_dir))
            elif cat == 'kartochka_vitrazha_po_km':
                parts.append(aggregate_kartochka_vitrazha(data_dir))
            elif cat == 'zns_po_kmd':
                parts.append(aggregate_zns_po_kmd(data_dir))

        if not parts:
            parts.append(aggregate_kmd(data_dir))

    data_date = _get_data_date(data_dir)
    header = f"Данные актуальны на: {data_date}\n\n" if data_date else ''
    return header + '\n\n'.join(parts)
