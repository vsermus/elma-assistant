import json
from datetime import datetime

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, dict) and 'result' in data:
            res = data['result']
            if isinstance(res, dict) and 'result' in res:
                return res['result']
            return res
        return data

def get_id(val):
    if isinstance(val, list):
        return val[0] if len(val) > 0 else None
    return val

def get_cents(val):
    if isinstance(val, dict) and 'cents' in val:
        return val['cents']
    return 0

def process_data():
    works = load_json('data/raboty_po_tenderu.json')
    tenders = {item['__id']: item for item in load_json('data/tender.json')}
    objects = {item['__id']: item for item in load_json('data/spravochnik_id.json')}
    companies = {item['__id']: item for item in load_json('data/_companies.json')}
    users = {item['__id']: item for item in load_json('data/users.json')}

    processed = []

    for work in works:
        # Joins
        tender_id = get_id(work.get('tender'))
        obj_id = get_id(work.get('id_proekta_1'))
        cust_id = get_id(work.get('zakazchik'))
        rp_id = get_id(work.get('rukovoditel_proekta'))
        teo_id = get_id(work.get('otvetstvennyi_v_teo'))
        init_id = get_id(work.get('iniciator_rabot_1'))

        tender = tenders.get(tender_id, {})
        obj = objects.get(obj_id, {})
        cust = companies.get(cust_id, {})
        rp = users.get(rp_id, {})
        teo = users.get(teo_id, {})
        init = users.get(init_id, {})

        # Costs
        montazh_cents = get_cents(work.get('montazh'))
        materialy_cents = get_cents(work.get('materialy'))
        total_cents = montazh_cents + materialy_cents

        total_rub = total_cents / 100.0
        montazh_rub = montazh_cents / 100.0
        materialy_rub = materialy_cents / 100.0

        kvadratura = work.get('kvadratura') or 0
        price_m2 = (total_rub / kvadratura) if kvadratura > 0 else 0

        # Date
        created_at = work.get('__createdAt')
        year = ""
        month = ""
        if created_at:
            try:
                dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
                year = str(dt.year)
                month = str(dt.month).zfill(2)
            except:
                pass

        # Work Type
        tip_rabot_data = work.get('tip_rabot')
        work_type = "Не указан"
        if isinstance(tip_rabot_data, list) and len(tip_rabot_data) > 0:
            first_item = tip_rabot_data[0]
            if isinstance(first_item, dict):
                work_type = first_item.get('name', "Не указан")
        elif isinstance(tip_rabot_data, str):
            work_type = tip_rabot_data
        else:
            # Fallback to tender if still not found
            tender_tipy = tender.get('tipy_rabot')
            if isinstance(tender_tipy, list) and len(tender_tipy) > 0:
                first_item = tender_tipy[0]
                if isinstance(first_item, dict):
                    work_type = first_item.get('name', "Не указан")
            elif isinstance(tender_tipy, str):
                work_type = tender_tipy

        processed.append({
            "id": work.get('__id'),
            "название": work.get('__name'),
            "тип_работы": work_type,
            "объект": obj.get('kodovoe_nazvanie') or obj.get('__name') or "Не указан",
            "тендер": tender.get('__name') or "Не указан",
            "заказчик": cust.get('name') or cust.get('__name') or "Не указан",
            "руководитель_проекта": rp.get('__name') or "Не указан",
            "ответственный_в_тео": teo.get('__name') or "Не указан",
            "инициатор_работ": init.get('__name') or "Не указан",
            "квадратура": kvadratura,
            "стоимость_монтажа": montazh_rub,
            "стоимость_материалов": materialy_rub,
            "общая_стоимость": total_rub,
            "цена_за_м2": price_m2,
            "год": year,
            "месяц": month,
            "дата_создания": created_at
        })

    with open('data/processed_tender_works.json', 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    process_data()
