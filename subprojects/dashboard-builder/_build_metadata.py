"""Auto-detect field types for dashboard builder"""
import json, os, re
from datetime import datetime

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
OUT = os.path.join(os.path.dirname(__file__), 'config', 'field_metadata.json')

# Russian translations for common field names
TRANSLATIONS = {
    '__id': 'ID записи',
    '__name': 'Название',
    '__createdAt': 'Дата создания',
    '__updatedAt': 'Дата изменения',
    '__createdBy': 'Создатель',
    '__updatedBy': 'Редактор',
    '__status': 'Статус',
    '__version': 'Версия',
    '__subscribers': 'Подписчики',
    '__deletedAt': 'Дата удаления',
    'fullname': 'ФИО',
    'login': 'Логин',
    'email': 'Email',
    'owner': 'Владелец',
    'mobilePhone': 'Телефон',
    'workPhone': 'Раб. телефон',
    'birthDate': 'Дата рождения',
    'hireDate': 'Дата приёма',
    'timezone': 'Часовой пояс',
    'displayedPosition': 'Должность',
    'groupIds': 'Группы',
    'osIds': 'ОС ID',
    'avatar': 'Аватар',
    'additionalData': 'Доп. данные',
    'type': 'Тип',
}

# Per-entity field translations
ENTITY_TRANSLATIONS = {
    'raboty_po_tenderu': {
        'id': 'ID работы',
        '__id': 'ID записи',
        'tender': 'Ссылка на тендер',
        '__name': 'Название работы',
        'tip_rabot': 'Типы работ',
        'tip_code': 'Код типа работ',
        'tip_name': 'Тип работ',
        'zakazchik': 'Заказчик',
        'id_proekta': 'ID проекта',
        'id_proekta_1': 'ID объекта',
        'kontragent': 'Контрагент',
        'kvadratura': 'Площадь, м²',
        'cena_m2': 'Цена за м²',
        'summa_kontrakta': 'Сумма контракта',
        'materialy': 'Материалы',
        'materialy_m2': 'Материалы за м²',
        'montazh': 'Монтаж',
        'montazh_m2': 'Монтаж за м²',
        'profil_m2': 'Профиль за м²',
        'profil': 'Профиль',
        'metizy_m2': 'Метизы за м²',
        'metizy': 'Метизы',
        'furnitura_m2': 'Фурнитура за м²',
        'furnitura': 'Фурнитура',
        'uplotniteli_m2': 'Уплотнители за м²',
        'uplotniteli': 'Уплотнители',
        'zapolneniya_m2': 'Заполнения за м²',
        'zapolneniya': 'Заполнения',
        'germetiki_klei_m2': 'Герметики/клей за м²',
        'germetiki_klei': 'Герметики/клей',
        'izgotovlenie_m2': 'Изготовление за м²',
        'izgotovlenie': 'Изготовление',
        'proektirovanie_m2': 'Проектирование за м²',
        'proektirovanie': 'Проектирование',
        'transportnye_m2': 'Транспортные за м²',
        'transportnye': 'Транспортные',
        'zarplata_m2': 'Зарплата за м²',
        'zarplata': 'Зарплата',
        'specodezhda_m2': 'Спецодежда за м²',
        'specodezhda': 'Спецодежда',
        'aksessuary_m2': 'Аксессуары за м²',
        'aksessuary': 'Аксессуары',
        'reklamacii_m2': 'Рекламации за м²',
        'reklamacii': 'Рекламации',
        'geodeziya_m2': 'Геодезия за м²',
        'geodeziya': 'Геодезия',
        'kronshteiny_v2': 'Кронштейны v2',
        'kronshteiny': 'Кронштейны',
        'primykaniya_m2': 'Примыкания за м²',
        'primykaniya': 'Примыкания',
        'ankera_m2': 'Анкера за м²',
        'ankera': 'Анкера',
        'genpodryadnye_m2': 'Генподрядные за м²',
        'genpodryadnye': 'Генподрядные',
        'subpodryadchiki_m2': 'Субподрядчики за м²',
        'subpodryadchiki': 'Субподрядчики',
        'prochie_raskhody_m2': 'Прочие расходы за м²',
        'prochie_raskhody': 'Прочие расходы',
        'itogo_raskhody_m2': 'Итого расходы за м²',
        'itogo_raskhody': 'Итого расходы',
        'dvu_m2': 'ДВУ за м²',
        'dvu': 'ДВУ',
        'podsobnye_rabochiem2': 'Подсобные рабочие за м²',
        'podsobnye_rabochie': 'Подсобные рабочие',
        'tualetnye_kabinki_m2': 'Туалетные кабинки за м²',
        'tualetnye_kabinki': 'Туалетные кабинки',
        'komandirovochnye_raskhody_m2': 'Командировочные за м²',
        'komandirovochnye_raskhody': 'Командировочные',
        'predstavitelskie_raskhody_m2': 'Представительские за м²',
        'predstavitelskie_raskhody': 'Представительские',
        'raskhody_na_prozhivanie_m2': 'Проживание за м²',
        'raskhody_na_prozhivanie': 'Проживание',
        'sdacha_sks_dolshikam_m2': 'Сдача СКС дольщикам за м²',
        'sdacha_sks_dolshikam': 'Сдача СКС дольщикам',
        'konsultacionnye_uslugi_m2': 'Консультационные за м²',
        'konsultacionnye_uslugi': 'Консультационные',
        'uslugi_podryadchikov_m2': 'Услуги подрядчиков за м²',
        'uslugi_podryadchikov': 'Услуги подрядчиков',
        'uslugi_kliningovoi_kompanii_m2': 'Клининг за м²',
        'uslugi_kliningovoi_kompanii': 'Клининг',
        'okhrana_truda_i_tekhnika_bezopasnosti_m2': 'Охрана труда за м²',
        'okhrana_truda_i_tekhnika_bezopasnosti': 'Охрана труда',
        'arenda_stroitelnoi_tekhniki_m2': 'Аренда техники за м²',
        'arenda_stroitelnoi_tekhniki': 'Аренда техники',
        'garantiinoe_obsluzhivanie_m2': 'Гарантийное обслуживание за м²',
        'garantiinoe_obsluzhivanie': 'Гарантийное обслуживание',
        'genpodryadnye_vozmeshenie_m2': 'Возмещение генподрядных за м²',
        'genpodryadnye_vozmeshenie': 'Возмещение генподрядных',
        'proektirovanie_i_geodeziya_m2': 'Проектирование и геодезия за м²',
        'proektirovanie_i_geodeziya': 'Проектирование и геодезия',
        'dvu_dok_obespechenie_stroitelstva_m2': 'ДВУ обеспечение стр. за м²',
        'dvu_dok_obespechenie_stroitelstva': 'ДВУ обеспечение стр.',
        'dvu_stoimost_kreditovaniya_m2': 'ДВУ стоимость кредит. за м²',
        'dvu_stoimost_kreditovaniya': 'ДВУ стоимость кредит.',
        'dok_obespechenie_stroitelstva_ppr_m2': 'Док. обеспечение стр. за м²',
        'dok_obespechenie_stroitelstva_ppr': 'Док. обеспечение стр.',
        'vyvoz_musora_i_promyshl_otkhodov_m2': 'Вывоз мусора за м²',
        'vyvoz_musora_i_promyshl_otkhodov': 'Вывоз мусора',
        'raskhodnye_materialy_m2': 'Расходные материалы за м²',
        'raskhodnye_materialy': 'Расходные материалы',
        'proizvodstvennyi_instrument_m2': 'Производственный инструмент за м²',
        'proizvodstvennyi_instrument': 'Производственный инструмент',
        'raskhody_sverkh_byudzheta_m2': 'Расходы сверх бюджета за м²',
        'raskhody_sverkh_byudzheta': 'Расходы сверх бюджета',
        'raskhody_na_poluchenie_sredstv_m2': 'Расходы на получение средств за м²',
        'raskhody_na_poluchenie_sredstv': 'Расходы на получение средств',
        'dokhod_ot_okazaniya_uslug_m2': 'Доход от услуг за м²',
        'dokhod_ot_okazaniya_uslug': 'Доход от услуг',
        'dokhod_m2': 'Доход за м²',
        'raskhody_m2': 'Расходы за м²',
        'zarplata_premialnaya_chast_m2': 'Премиальная часть ЗП за м²',
        'zarplata_premialnaya_chast': 'Премиальная часть ЗП',
        'rukovoditel_proekta': 'Руководитель проекта (РП)',
        'rukovoditel_sd': 'Руководитель СД',
        'rukovoditel_montazhnogo_otdela': 'Руководитель монтажного отдела',
        'iniciator_rabot_1': 'Инициатор работ',
        'iniciator_rabot': 'Инициатор работ',
        'otvetstvennyi_v_teo': 'Ответственный в ТЭО',
        'nasha_organizaciya': 'Наша организация',
        'kommentarii_ds': 'Комментарий ДС',
        'kommentarii_mo': 'Комментарий МО',
        'kommentarii_os': 'Комментарий ОС',
        'osobye_usloviya': 'Особые условия',
        'data_nachala_rabot': 'Дата начала работ',
        'data_nachala_rabot_1': 'Дата начала работ (2)',
        'data_okonchaniya': 'Дата окончания',
        'srok_nachala_stroitelstva': 'Срок начала строительства',
        'predpolagaemaya_data_okonchaniya_stroitelstva': 'Предп. дата окончания',
        'rezultat_tendera': 'Результат тендера',
        'pobeditel_tendera': 'Победитель тендера',
        'tip_rabot': 'Типы работ',
        '__status': 'Статус',
        'faily_ar': 'Файлы АР',
        'faily_tz': 'Файлы ТЗ',
        'faily_kp_oferta': 'Файлы КП/оферта',
        'proforma_dogovora': 'Проформа договора',
        'faily_predv_rascheta': 'Файлы предв. расчёта',
        'faily_s_cenami': 'Файлы с ценами',
        'faily_iz_os': 'Файлы из ОС',
        'vypolnit_raschet': 'Выполнить расчёт',
        'vypolnit_proverku_proekta': 'Проверка проекта',
        'neobkhodimost_proverki_obyomov_rabot': 'Проверка объёмов работ',
        '__tasks': 'Задачи',
        '__tasks_performers': 'Исполнители задач',
        '__tasks_earliest_duedate': 'Ранний срок задач',
        'tendernyi_byudzhet': 'Тендерный бюджет',
        'kratkoe_nazvanie_obekta': 'Объект (кратко)',
        'stroitelnyi_adres_obekta': 'Адрес объекта',
        'kontakty_po_obektu': 'Контакты по объекту',
        'nasha_organizaciya': 'Наша организация',
        'protokol_itogov_tendera': 'Протокол итогов тендера',
        'skvoznoi_kommentarii_v_osnovnoi_forme_tendera': 'Сквозной комментарий',
        'faily_raschetov_s_ponizhenizhennoi_marzhinalnostyu': 'Файлы расчётов с пониж. марж.',
        '__externalProcessMeta': 'Метаданные процесса',
        '__directory': 'Директория',
        '__externalId': 'Внешний ID',
        '__debug': 'Отладка',
        '__index': 'Индекс',
    },
    'tender': {
        '__id': 'ID тендера',
        '__name': 'Название тендера',
        '__status': 'Статус',
        'tender_variants': 'Варианты тендера',
        'dochernie_processy_tendera': 'Дочерние процессы',
        'tablica_dochernikh_processov': 'Таблица дочерних процессов',
        'tipy_rabot': 'Типы работ',
        'spisok_tipov_rabot': 'Список типов работ',
        'spisok_tipov_rabot_kody': 'Коды типов работ',
        'spisok_tipov_rabot_nazvaniya': 'Названия типов работ',
        'zakazchik': 'Заказчик',
        'id_proekta_1': 'ID объекта',
        'city': 'Город',
        'region': 'Регион',
        'counrty': 'Страна',
        'nasha_organizaciya': 'Наша организация',
        'rukovoditel_proekta': 'Руководитель проекта',
        'rukovoditel_sd': 'Руководитель СД',
        'rukovoditel_montazhnogo_otdela': 'Руководитель монтажного отдела',
        'iniciator_rabot_1': 'Инициатор работ',
        'otvetstvennyi_v_teo': 'Ответственный в ТЭО',
        'pobeditel_tendera': 'Победитель тендера',
        'rezultat_tendera': 'Результат тендера',
        'rezultat_tendera_txt': 'Результат тендера (текст)',
        'data_nachala_tendera': 'Дата начала тендера',
        'data_okonchaniya_tendera': 'Дата окончания тендера',
        'data_okonchaniya': 'Дата окончания',
        'data_nachala_rabot_1': 'Дата начала работ',
        'srok_nachala_stroitelstva': 'Срок начала строительства',
        'predpolagaemaya_data_okonchaniya_stroitelstva': 'Предп. дата окончания',
        'kvadratura': 'Площадь, м²',
        'summa_kontrakta': 'Сумма контракта',
        'itogo_cena_kontrakta': 'Итого цена контракта',
        'stoimost_kontrakta': 'Стоимость контракта',
        'itogovaya_summa_tendera': 'Итоговая сумма тендера',
        'tendernyi_byudzhet': 'Тендерный бюджет',
        'materialy': 'Материалы',
        'materialy_m2': 'Материалы за м²',
        'montazh': 'Монтаж',
        'montazh_m2': 'Монтаж за м²',
        'profil': 'Профиль',
        'profil_m2': 'Профиль за м²',
        'metizy': 'Метизы',
        'metizy_m2': 'Метизы за м²',
        'furnitura': 'Фурнитура',
        'furnitura_m2': 'Фурнитура за м²',
        'uplotniteli': 'Уплотнители',
        'uplotniteli_m2': 'Уплотнители за м²',
        'zapolneniya': 'Заполнения',
        'zapolneniya_m2': 'Заполнения за м²',
        'germetiki_klei': 'Герметики/клей',
        'germetiki_klei_m2': 'Герметики/клей за м²',
        'izgotovlenie': 'Изготовление',
        'izgotovlenie_m2': 'Изготовление за м²',
        'proektirovanie': 'Проектирование',
        'proektirovanie_m2': 'Проектирование за м²',
        'transportnye': 'Транспортные',
        'transportnye_m2': 'Транспортные за м²',
        'zarplata': 'Зарплата',
        'zarplata_m2': 'Зарплата за м²',
        'subpodryadchiki': 'Субподрядчики',
        'subpodryadchiki_m2': 'Субподрядчики за м²',
        'prochie_raskhody': 'Прочие расходы',
        'prochie_raskhody_m2': 'Прочие расходы за м²',
        'dvu': 'ДВУ',
        'dvu_m2': 'ДВУ за м²',
        'chistaya_pribyl': 'Чистая прибыль',
        'chistaya_pribyl_procent': 'Чистая прибыль, %',
        'cf_chistyi': 'Чистый CF',
        'cf_chistyi_procent': 'Чистый CF, %',
        'cf_bez_naloga_na_pribyl': 'CF без налога на прибыль',
        'cf_bez_naloga_na_pribyl_procent': 'CF без налога на прибыль, %',
        'nalog_na_pribyl': 'Налог на прибыль',
        'nakladnye_s_nds': 'Накладные с НДС',
        'nakladnye_s_nds_percent': 'Накладные с НДС, %',
        'nds_k_uplate': 'НДС к уплате',
        'nds_20_ot_kontrakta': 'НДС 20% от контракта',
        'nds_20_k_vychetu_za_matly_i_uslugi_vkhod': 'НДС к вычету (мат-лы) вход',
        'nds_20_k_vychetu_za_nakladnye_vkhodyashii': 'НДС к вычету (накладные) вход',
        'nacenka': 'Наценка',
        'uderzhanie': 'Удержание',
        'uderzhanie_percent': 'Удержание, %',
        'kratkoe_nazvanie_obekta': 'Объект (кратко)',
        'stroitelnyi_adres_obekta': 'Адрес объекта',
        'pole_dlya_peresokhraneniya_zagolovka': 'Заголовок',
        'temp_id': 'Временный ID',
        'protokol_itogov_tendera': 'Протокол итогов',
        'disagreements_protocol': 'Протокол разногласий',
        'proforma_dogovora': 'Проформа договора',
        'varianty_zaklyucheniya_dogovora': 'Варианты договора',
        'kommentarii_sotrudniku_teo': 'Комментарий ТЭО',
        'faily_ar': 'Файлы АР',
        'faily_tz': 'Файлы ТЗ',
        'faily_iz_mo': 'Файлы из МО',
        'faily_iz_os': 'Файлы из ОС',
        'faily_iz_sd': 'Файлы из СД',
        'faily_kp_oferta': 'Файлы КП/оферта',
        'faily_s_cenami': 'Файлы с ценами',
        'faily_predv_rascheta': 'Файлы предв. расчёта',
        'vypolnit_raschet': 'Выполнить расчёт',
        'vypolnit_proverku_proekta': 'Проверка проекта',
        'neobkhodimost_proverki_obyomov_rabot': 'Проверка объёмов',
        'okhrana_truda_i_tekhnika_bezopasnosti': 'Охрана труда',
        'okhrana_truda_i_tekhnika_bezopasnosti_m2': 'Охрана труда за м²',
        'skvoznoi_kommentarii_v_osnovnoi_forme_tendera': 'Сквозной комментарий',
        'faily_raschetov_s_ponizhenizhennoi_marzhinalnostyu': 'Файлы с пониж. марж.',
        '__externalProcessMeta': 'Метаданные процесса',
    },
    'spravochnik_id': {
        '__id': 'ID записи',
        '__name': 'Название объекта',
        'itogovyi_id': 'Итоговый ID',
        'cifrovaya_chast_id': 'Цифровая часть ID',
        'bukvennaya_chast_id': 'Буквенная часть ID',
        'bukvennaya_chast_id_txt': 'Буквенная часть ID (текст)',
        'kodovoe_nazvanie': 'Кодовое название',
        'dogovor_txt': 'Договор',
        'stroitelnyi_adres': 'Строительный адрес',
        'policeiskii_adres': 'Полицейский адрес',
        'city': 'Город',
        'region': 'Регион',
        'client': 'Клиент',
        'zakazchik': 'Заказчик',
        'zakazchik_po_crm': 'Заказчик (CRM)',
        'kontragent': 'Контрагент',
        'nasha_kompaniya': 'Наша компания',
        'rukovoditel_proekta': 'Руководитель проекта',
        'rukovoditel_stroitelnoi_direkcii': 'Руководитель СД',
        'montazhnoe_podrazdelenie': 'Монтажное подразделение',
        'raboty_po_tenderu': 'Работы по тендеру',
        'data_zavedeniya_id': 'Дата заведения ID',
    },
    '_companies': {
        '__id': 'ID компании',
        '__name': 'Название компании',
        'type': 'Тип',
        'type_of_agent': 'Тип агента',
        'tip_kontragenta': 'Тип контрагента',
        'otrasl': 'Отрасль',
        '_segment': 'Сегмент',
        'sale_segment': 'Сегмент продаж',
        '_industries': 'Индустрии',
        'responsible': 'Ответственный',
        '_leads': 'Лиды',
        '_opportunities': 'Сделки',
        '_parentCompany': 'Головная компания',
        '_childCompanies': 'Дочерние компании',
        '_inn': 'ИНН',
        '_kpp': 'КПП',
        '_ogrn': 'ОГРН',
        '_bik': 'БИК',
        '_bank': 'Банк',
        'bank': 'Банк',
        'bic': 'BIC',
        '_address': 'Адрес',
        '_legalAddress': 'Юридический адрес',
        '_legalName': 'Юридическое название',
        '_correspondenceAddress': 'Адрес для корреспонденции',
        '_operatingAccount': 'Расчётный счёт',
        '_correspondentAccount': 'Корр. счёт',
        'correspondent_account': 'Корр. счёт',
        'payment_account': 'Платёжный счёт',
        'bank_details': 'Банковские реквизиты',
        'ogrn': 'ОГРН',
        'name': 'Название',
        '_email': 'Email',
        '_phone': 'Телефон',
        '_website': 'Веб-сайт',
        'files': 'Файлы',
        'agreement': 'Соглашение',
        'base_action': 'Базовое действие',
        'fio_signatory': 'ФИО подписанта',
        'signatory_position': 'Должность подписанта',
        'search_string': 'Поисковая строка',
        'showsuggestions': 'Показывать подсказки',
        'opf': 'ОПФ',
        'marketingovoe_meropriyatiya': 'Маркетинговые мероприятия',
        'sotrudnik_vneshnei_organizacii': 'Сотрудник внешней организации',
        '_contacts': 'Контакты',
    },
    'users': {
        '__id': 'ID пользователя',
        '__name': 'ФИО',
        'fullname': 'ФИО (полностью)',
        'login': 'Логин',
        'email': 'Email',
        'owner': 'Владелец',
        'mobilePhone': 'Мобильный телефон',
        'workPhone': 'Рабочий телефон',
        'birthDate': 'Дата рождения',
        'hireDate': 'Дата приёма',
        'timezone': 'Часовой пояс',
        'displayedPosition': 'Должность',
        'groupIds': 'Группы',
        'osIds': 'ОС ID',
        'avatar': 'Аватар',
        'additionalData': 'Доп. данные',
    },
    'statusy_rabot_po_tenderam': {
        'id': 'ID статуса',
        'name': 'Название статуса',
        'code': 'Код статуса',
        'groupId': 'Группа статуса',
    },
}

DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


def detect_type(entity_id: str, field: str, val, all_records):
    """Auto-detect field type"""
    # System fields
    if field == '__debug' or field == '__index':
        return 'skip'

    # Find non-None values
    sample = None
    for r in all_records:
        v = r.get(field)
        if v is not None:
            sample = v
            break

    if sample is None:
        # Try another approach
        for r in all_records:
            v = r.get(field)
            if v is not None:
                sample = v
                break

    if sample is None:
        return 'skip'

    stype = type(sample).__name__

    # bool
    if stype == 'bool':
        return 'dimension'

    # int or float without money structure
    if stype in ('int', 'float'):
        return 'metric'

    # Money dict like {"cents": 12345, "currency": "RUB"}
    if stype == 'dict':
        keys = list(sample.keys())
        if 'cents' in keys and 'currency' in keys:
            return 'metric'
        else:
            return 'skip'

    # Date string
    if stype == 'str' and DATE_PATTERN.match(sample):
        return 'date'

    # String
    if stype == 'str':
        return 'dimension'

    # List
    if stype == 'list':
        return 'link'

    return 'skip'


def get_russian(entity_id: str, field: str) -> str:
    """Get Russian name for a field"""
    # Check entity-specific translations
    if entity_id in ENTITY_TRANSLATIONS:
        if field in ENTITY_TRANSLATIONS[entity_id]:
            return ENTITY_TRANSLATIONS[entity_id][field]
    # Check global translations
    if field in TRANSLATIONS:
        return TRANSLATIONS[field]
    # Auto-translate
    name = field.replace('_m2', ' за м²').replace('_', ' ').strip()
    return name


def main():
    entities_config_path = os.path.join(ROOT, 'config', 'entities.json')
    with open(entities_config_path, encoding='utf-8') as f:
        entities_config = json.load(f)

    selected = {'raboty_po_tenderu', 'tender', 'spravochnik_id', '_companies', 'users', 'statusy_rabot_po_tenderam'}
    result = []

    for ent in entities_config:
        eid = ent['id']
        if eid not in selected:
            continue

        path = os.path.join(ROOT, 'data', f'{eid}.json')
        if not os.path.exists(path):
            print(f'{eid}: file not found, skip')
            continue

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        records = None
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            if 'result' in data and isinstance(data['result'], dict) and 'result' in data['result']:
                records = data['result']['result']
            elif 'result' in data and isinstance(data['result'], list):
                records = data['result']
            elif 'statusItems' in data:
                records = data['statusItems']
            elif 'items' in data:
                records = data['items']

        if not records:
            print(f'{eid}: no records, skip')
            continue

        fields_config = []
        for field in records[0].keys():
            first_val = records[0][field]
            ftype = detect_type(eid, field, first_val, records)
            russian = get_russian(eid, field)

            # Check if this is a link to another entity
            link_to = None
            if ftype == 'link':
                # Try to determine what it links to based on field name
                link_targets = {
                    'zakazchik': '_companies',
                    'client': '_companies',
                    'kontragent': '_companies',
                    'nasha_kompaniya': '_companies',
                    'nasha_organizaciya': '_companies',
                    'id_proekta': 'spravochnik_id',
                    'id_proekta_1': 'spravochnik_id',
                    'rukovoditel_proekta': 'users',
                    'rukovoditel_sd': 'users',
                    'rukovoditel_montazhnogo_otdela': 'users',
                    'iniciator_rabot_1': 'users',
                    'iniciator_rabot': 'users',
                    'otvetstvennyi_v_teo': 'users',
                    'responsible': 'users',
                    'pobeditel_tendera': '_companies',
                    'tender': 'tender',
                    'zakazchik_po_crm': '_companies',
                    'rukovoditel_stroitelnoi_direkcii': 'users',
                    'montazhnoe_podrazdelenie': 'users',
                    'client': '_companies',
                }
                link_to = link_targets.get(field)

            field_entry = {
                'key': field,
                'name': russian,
                'type': ftype,
            }
            if link_to:
                field_entry['linkTo'] = link_to
            fields_config.append(field_entry)

        result.append({
            'id': eid,
            'name': ent['name'],
            'description': ent.get('description', ''),
            'fields': fields_config,
        })

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Summary
    for ent in result:
        metrics = sum(1 for f in ent['fields'] if f['type'] == 'metric')
        dims = sum(1 for f in ent['fields'] if f['type'] == 'dimension')
        dates = sum(1 for f in ent['fields'] if f['type'] == 'date')
        links = sum(1 for f in ent['fields'] if f['type'] == 'link')
        skipped = sum(1 for f in ent['fields'] if f['type'] == 'skip')
        print(f'{ent["name"]}: {metrics} метрик, {dims} измерений, {dates} дат, {links} связей, {skipped} скрыто')
    print(f'\nСохранено в {OUT}')


if __name__ == '__main__':
    main()
