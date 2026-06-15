// ========================================================
// СПРАВОЧНИК КОМПАНИЙ — загрузка данных из ELMA365 в Power BI
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- Параметры ---
    БазовыйURL = "https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/_clients/_companies/list",
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
        "__id", "__name",
        "__createdAt", "__createdBy", "__updatedAt", "__updatedBy",
        "_inn", "_kpp", "_ogrn",
        "_legalName", "_address", "_legalAddress",
        "_bank", "_bik",
        "_phone", "_email", "_website",
        "type", "opf", "type_of_agent",
        "responsible", "fio_signatory", "base_action",
        "otrasl", "search_string"
    }),

    // --- _phone: список телефонов → первый номер ---
    ИзвлечьТелефон = Table.TransformColumns(
        ВыборКолонок,
        {"_phone",
            each
                if _ is list and List.Count(_) > 0
                then _{0}[tel]
                else null,
            type text}
    ),

    // --- _email: список email'ов → первый ---
    ИзвлечьEmail = Table.TransformColumns(
        ИзвлечьТелефон,
        {"_email",
            each
                if _ is list and List.Count(_) > 0
                then _{0}[email]
                else null,
            type text}
    ),

    // --- opf, type_of_agent, otrasl: список → текст ---
    ИзвлечьСписки = Table.TransformColumns(
        ИзвлечьEmail, {
            {"opf",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text},
            {"type_of_agent",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text},
            {"otrasl",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text}
        }
    ),

    // --- responsible: список ID → первый ---
    ИзвлечьОтветственного = Table.TransformColumns(
        ИзвлечьСписки,
        {"responsible",
            each if _ is list and List.Count(_) > 0 then _{0} else null,
            type text}
    ),

    // --- fio_signatory: record → Фамилия И.О. ---
    ИзвлечьПодписанта = Table.TransformColumns(
        ИзвлечьОтветственного,
        {"fio_signatory",
            each
                if _ is record then
                    Text.Trim(
                        (_[lastname] ?? "") & " "
                        & (Text.Start(_[firstname] ?? "", 1) & ".")
                        & (Text.Start(_[middlename] ?? "", 1) & ".")
                    )
                else null,
            type text}
    ),

    // --- Удаляем полностью пустые колонки ---
    УдалитьПустые = Table.SelectColumns(
        ИзвлечьПодписанта,
        List.Select(
            Table.ColumnNames(ИзвлечьПодписанта),
            each List.NonNullCount(Table.Column(ИзвлечьПодписанта, _)) > 0
        )
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(УдалитьПустые, {
        {"__id", type text},
        {"__name", type text},
        {"__createdAt", type datetimezone},
        {"__createdBy", type text},
        {"__updatedAt", type datetimezone},
        {"__updatedBy", type text},
        {"_inn", type text},
        {"_kpp", type text},
        {"_ogrn", type text},
        {"_legalName", type text},
        {"_address", type text},
        {"_legalAddress", type text},
        {"_bank", type text},
        {"_bik", type text},
        {"_phone", type text},
        {"_email", type text},
        {"_website", type text},
        {"type", type logical},
        {"opf", type text},
        {"type_of_agent", type text},
        {"responsible", type text},
        {"fio_signatory", type text},
        {"base_action", type text},
        {"otrasl", type text},
        {"search_string", type text}
    }),

    // --- Перевод на русский ---
    Заказчики = Table.RenameColumns(Типизация, {
        {"__id", "ID компании"},
        {"__name", "Название"},
        {"__createdAt", "Дата создания"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedAt", "Дата изменения"},
        {"__updatedBy", "Кто изменил (ID)"},
        {"_inn", "ИНН"},
        {"_kpp", "КПП"},
        {"_ogrn", "ОГРН"},
        {"_legalName", "Юр. наименование"},
        {"_address", "Адрес"},
        {"_legalAddress", "Юр. адрес"},
        {"_bank", "Банк"},
        {"_bik", "БИК"},
        {"_phone", "Телефон"},
        {"_email", "Email"},
        {"_website", "Сайт"},
        {"type", "Юр. лицо"},
        {"opf", "ОПФ"},
        {"type_of_agent", "Тип агента"},
        {"responsible", "Ответственный (ID)"},
        {"fio_signatory", "Подписант"},
        {"base_action", "Основание"},
        {"otrasl", "Отрасль"},
        {"search_string", "Поисковая строка"}
    })
in
    Заказчики
