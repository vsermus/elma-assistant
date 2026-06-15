// ========================================================
// ТЕНДЕРЫ — загрузка данных из ELMA365 в Power BI
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// 4. При необходимости создайте параметр ТокенELMA
// ========================================================

let
    // --- Параметры ---
    БазовыйURL = "https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/tender/raboty_po_tenderu_1/list",
    Токен = "2ad06f66-6ecc-42b3-9bf4-1ef21eabb371",

    // --- Запрос к ELMA ---
    ПараметрыЗапроса = "{""size"": 10000}",
    ПолныйURL = БазовыйURL & "?query=" & Uri.EscapeDataString(ПараметрыЗапроса),

    // --- HTTP GET ---
    Ответ = Json.Document(
        Web.Contents(ПолныйURL, [
            Headers = [
                Authorization = "Bearer " & Токен,
                #"Content-Type" = "application/json"
            ]
        ])
    ),

    // --- Массив записей ---
    Данные = Ответ[result][result],

    // --- Собираем все поля из всех записей (у разных записей набор полей различается) ---
    ВсеПоля = List.Distinct(List.Combine(List.Transform(Данные, each Record.FieldNames(_)))),

    // --- В таблицу с явным списком полей и null для пропущенных ---
    Таблица = Table.FromRecords(Данные, ВсеПоля, MissingField.UseNull),

    // --- Выбор ключевых колонок ---
    ВыборКолонок = Table.SelectColumns(Таблица, {
        "__id", "__name", "__status",
        "__createdAt", "__createdBy",
        "__updatedAt", "__updatedBy",
        "kratkoe_nazvanie_obekta", "stroitelnyi_adres_obekta", "id_proekta_1",
        "zakazchik", "nasha_organizaciya",
        "iniciator_rabot_1", "rukovoditel_proekta", "rukovoditel_sd",
        "data_nachala_tendera", "data_okonchaniya_tendera",
        "data_nachala_rabot_1", "srok_nachala_stroitelstva",
        "predpolagaemaya_data_okonchaniya_stroitelstva",
        "tipy_rabot", "tender_variants", "pobeditel_tendera",
        "materialy", "montazh", "prochie_raskhody", "subpodryadchiki",
        "itogovaya_summa_tendera", "stoimost_kontrakta",
        "kvadratura", "osobye_usloviya"
    }),

    // --- __status: запись {order, status} → число (код статуса) ---
    ИзвлечьСтатус = Table.TransformColumns(
        ВыборКолонок,
        {"__status", each if _ is record then _[status] else null, Int64.Type}
    ),

    // --- Денежные поля {cents, currency} → рубли ---
    ИзвлечьСуммы = Table.TransformColumns(
        ИзвлечьСтатус, {
            {"materialy",
                each if _ is record then _[cents] / 100 else null, type number},
            {"montazh",
                each if _ is record then _[cents] / 100 else null, type number},
            {"prochie_raskhody",
                each if _ is record then _[cents] / 100 else null, type number},
            {"subpodryadchiki",
                each if _ is record then _[cents] / 100 else null, type number},
            {"itogovaya_summa_tendera",
                each if _ is record then _[cents] / 100 else null, type number},
            {"stoimost_kontrakta",
                each if _ is record then _[cents] / 100 else null, type number}
        }
    ),

    // --- Списки-ссылки: берём первый ID из массива ---
    ИзвлечьСсылки = Table.TransformColumns(
        ИзвлечьСуммы, {
            {"id_proekta_1",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"zakazchik",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"nasha_organizaciya",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"iniciator_rabot_1",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"rukovoditel_proekta",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"rukovoditel_sd",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"pobeditel_tendera",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text}
        }
    ),

    // --- tipy_rabot: список кодов → текст через "; " ---
    ИзвлечьТипыРабот = Table.TransformColumns(
        ИзвлечьСсылки,
        {"tipy_rabot",
            each
                if _ is list and List.Count(_) > 0
                then Text.Combine(List.Transform(_, each _[name]), "; ")
                else null,
            type text}
    ),

    // --- tender_variants: список вариантов → текст ---
    ИзвлечьВарианты = Table.TransformColumns(
        ИзвлечьТипыРабот,
        {"tender_variants",
            each
                if _ is list and List.Count(_) > 0
                then Text.Combine(List.Transform(_, each _[name]), "; ")
                else null,
            type text}
    ),

    // --- Типизация колонок ---
    Типизация = Table.TransformColumnTypes(ИзвлечьВарианты, {
        {"__id", type text},
        {"__name", type text},
        {"__status", Int64.Type},
        {"__createdAt", type datetimezone},
        {"__createdBy", type text},
        {"__updatedAt", type datetimezone},
        {"__updatedBy", type text},
        {"kratkoe_nazvanie_obekta", type text},
        {"stroitelnyi_adres_obekta", type text},
        {"id_proekta_1", type text},
        {"zakazchik", type text},
        {"nasha_organizaciya", type text},
        {"iniciator_rabot_1", type text},
        {"rukovoditel_proekta", type text},
        {"rukovoditel_sd", type text},
        {"data_nachala_tendera", type datetimezone},
        {"data_okonchaniya_tendera", type datetimezone},
        {"data_nachala_rabot_1", type datetimezone},
        {"srok_nachala_stroitelstva", type datetimezone},
        {"predpolagaemaya_data_okonchaniya_stroitelstva", type datetimezone},
        {"tipy_rabot", type text},
        {"tender_variants", type text},
        {"pobeditel_tendera", type text},
        {"materialy", type number},
        {"montazh", type number},
        {"prochie_raskhody", type number},
        {"subpodryadchiki", type number},
        {"itogovaya_summa_tendera", type number},
        {"stoimost_kontrakta", type number},
        {"kvadratura", Int64.Type},
        {"osobye_usloviya", type text}
    }),

    // --- Перевод названий колонок на русский ---
    ДатаБезВремени = Table.TransformColumns(Типизация, {
        {"data_nachala_tendera", Date.From, type date},
        {"data_okonchaniya_tendera", Date.From, type date},
        {"data_nachala_rabot_1", Date.From, type date},
        {"srok_nachala_stroitelstva", Date.From, type date},
        {"predpolagaemaya_data_okonchaniya_stroitelstva", Date.From, type date}
    }),

    Тендеры = Table.RenameColumns(ДатаБезВремени, {
        {"__id", "ID тендера"},
        {"__name", "Название"},
        {"__status", "Код статуса"},
        {"__createdAt", "Дата создания"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedAt", "Дата изменения"},
        {"__updatedBy", "Кто изменил (ID)"},
        {"kratkoe_nazvanie_obekta", "Объект"},
        {"stroitelnyi_adres_obekta", "Адрес объекта"},
        {"id_proekta_1", "ID объекта (справочник)"},
        {"zakazchik", "Заказчик (ID)"},
        {"nasha_organizaciya", "Наша организация (ID)"},
        {"iniciator_rabot_1", "Инициатор работ (ID)"},
        {"rukovoditel_proekta", "РП (ID)"},
        {"rukovoditel_sd", "РСД (ID)"},
        {"data_nachala_tendera", "Начало тендера"},
        {"data_okonchaniya_tendera", "Окончание тендера"},
        {"data_nachala_rabot_1", "Начало работ"},
        {"srok_nachala_stroitelstva", "Начало стр-ва"},
        {"predpolagaemaya_data_okonchaniya_stroitelstva", "Окончание стр-ва"},
        {"tipy_rabot", "Типы работ"},
        {"tender_variants", "Результат тендера"},
        {"pobeditel_tendera", "Победитель (ID)"},
        {"materialy", "Материалы, руб"},
        {"montazh", "Монтаж, руб"},
        {"prochie_raskhody", "Прочие расходы, руб"},
        {"subpodryadchiki", "Субподрядчики, руб"},
        {"itogovaya_summa_tendera", "Итоговая сумма, руб"},
        {"stoimost_kontrakta", "Стоимость контракта, руб"},
        {"kvadratura", "Площадь, м²"},
        {"osobye_usloviya", "Особые условия"}
    })
in
    Тендеры
