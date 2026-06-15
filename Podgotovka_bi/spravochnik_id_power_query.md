// ========================================================
// СПРАВОЧНИК ID ОБЪЕКТОВ СТРОИТЕЛЬСТВА — загрузка из ELMA365
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- Параметры ---
    БазовыйURL = "https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/_system_catalogs/spravochnik_id/list",
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

    // --- Собираем все поля ---
    ВсеПоля = List.Distinct(List.Combine(List.Transform(Данные, each Record.FieldNames(_)))),

    // --- В таблицу ---
    Таблица = Table.FromRecords(Данные, ВсеПоля, MissingField.UseNull),

    // --- Выбор колонок ---
    ВыборКолонок = Table.SelectColumns(Таблица, {
        "__id", "__name", "__status",
        "__createdAt", "__createdBy", "__updatedAt",
        "itogovyi_id", "cifrovaya_chast_id",
        "bukvennaya_chast_id", "bukvennaya_chast_id_txt",
        "kodovoe_nazvanie", "stroitelnyi_adres",
        "zakazchik", "client", "kontragent", "nasha_kompaniya",
        "rukovoditel_proekta", "rukovoditel_stroitelnoi_direkcii",
        "dogovor_txt", "raboty_po_tenderu",
        "data_zavedeniya_id", "city", "region"
    }),

    // --- __status → число ---
    ИзвлечьСтатус = Table.TransformColumns(
        ВыборКолонок,
        {"__status", each if _ is record then _[status] else null, Int64.Type}
    ),

    // --- Списки-ссылки: берём первый ID ---
    ИзвлечьСсылки = Table.TransformColumns(
        ИзвлечьСтатус, {
            {"zakazchik",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"client",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"kontragent",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"nasha_kompaniya",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"rukovoditel_proekta",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"rukovoditel_stroitelnoi_direkcii",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"raboty_po_tenderu",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text}
        }
    ),

    // --- city, region: список → текст через "; " ---
    ИзвлечьГорода = Table.TransformColumns(
        ИзвлечьСсылки, {
            {"city",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text},
            {"region",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text}
        }
    ),

    // --- Удаляем полностью пустые колонки ---
    УдалитьПустые = Table.SelectColumns(
        ИзвлечьГорода,
        List.Select(
            Table.ColumnNames(ИзвлечьГорода),
            each List.NonNullCount(Table.Column(ИзвлечьГорода, _)) > 0
        )
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(УдалитьПустые, {
        {"__id", type text},
        {"__name", type text},
        {"__status", Int64.Type},
        {"__createdAt", type datetimezone},
        {"__createdBy", type text},
        {"__updatedAt", type datetimezone},
        {"itogovyi_id", type text},
        {"cifrovaya_chast_id", type text},
        {"bukvennaya_chast_id", type text},
        {"bukvennaya_chast_id_txt", type text},
        {"kodovoe_nazvanie", type text},
        {"stroitelnyi_adres", type text},
        {"zakazchik", type text},
        {"client", type text},
        {"kontragent", type text},
        {"nasha_kompaniya", type text},
        {"rukovoditel_proekta", type text},
        {"rukovoditel_stroitelnoi_direkcii", type text},
        {"dogovor_txt", type text},
        {"raboty_po_tenderu", type text},
        {"data_zavedeniya_id", type datetimezone},
        {"city", type text},
        {"region", type text}
    }),

    // --- Перевод на русский ---
    ДатаБезВремени = Table.TransformColumns(Типизация, {
        {"data_zavedeniya_id", Date.From, type date}
    }),

    Справочники_ID = Table.RenameColumns(ДатаБезВремени, {
        {"__id", "ID записи"},
        {"__name", "Название"},
        {"__status", "Код статуса"},
        {"__createdAt", "Дата создания"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedAt", "Дата изменения"},
        {"itogovyi_id", "Итоговый ID"},
        {"cifrovaya_chast_id", "Цифровая часть"},
        {"bukvennaya_chast_id", "Буквенная часть (код)"},
        {"bukvennaya_chast_id_txt", "Буквенная часть (текст)"},
        {"kodovoe_nazvanie", "Кодовое название"},
        {"stroitelnyi_adres", "Строительный адрес"},
        {"zakazchik", "Заказчик (ID)"},
        {"client", "Клиент (ID)"},
        {"kontragent", "Контрагент (ID)"},
        {"nasha_kompaniya", "Наша компания (ID)"},
        {"rukovoditel_proekta", "РП (ID)"},
        {"rukovoditel_stroitelnoi_direkcii", "РСД (ID)"},
        {"dogovor_txt", "Договор"},
        {"raboty_po_tenderu", "Работы по тендеру (ID)"},
        {"data_zavedeniya_id", "Дата заведения"},
        {"city", "Город"},
        {"region", "Регион"}
    })
in
    Справочники_ID
