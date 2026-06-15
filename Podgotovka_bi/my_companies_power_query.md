// ========================================================
// НАШИ КОМПАНИИ — загрузка данных из ELMA365 в Power BI
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- Параметры ---
    БазовыйURL = "https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/_system_catalogs/_my_companies/list",
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
        "_full_legal_name", "_legal_address", "_actual_address",
        "_bank", "_bik",
        "_transactional_account", "_correspondent_account",
        "_phone", "_email",
        "web",
        "_director", "signatory", "signatory_position",
        "base_action", "custom_okpo", "correspondenceAddress",
        "agreements", "SETTINGS_KS_REPORT_ENABLED"
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

    // --- _director, signatory: список ID → первый ID ---
    ИзвлечьСсылки = Table.TransformColumns(
        ИзвлечьEmail, {
            {"_director",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"signatory",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"__createdBy",
                each if _ is list and List.Count(_) > 0 then _{0} else _, type text},
            {"__updatedBy",
                each if _ is list and List.Count(_) > 0 then _{0} else _, type text}
        }
    ),

    // --- SETTINGS_KS_REPORT_ENABLED: логическое ---
    ИзвлечьБулево = Table.TransformColumns(
        ИзвлечьСсылки,
        {"SETTINGS_KS_REPORT_ENABLED", each _ = true, type logical}
    ),

    // --- Удаляем полностью пустые колонки ---
    УдалитьПустые = Table.SelectColumns(
        ИзвлечьБулево,
        List.Select(
            Table.ColumnNames(ИзвлечьБулево),
            each List.NonNullCount(Table.Column(ИзвлечьБулево, _)) > 0
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
        {"_full_legal_name", type text},
        {"_legal_address", type text},
        {"_actual_address", type text},
        {"_bank", type text},
        {"_bik", type text},
        {"_transactional_account", type text},
        {"_correspondent_account", type text},
        {"_phone", type text},
        {"_email", type text},
        {"web", type text},
        {"_director", type text},
        {"signatory", type text},
        {"signatory_position", type text},
        {"base_action", type text},
        {"custom_okpo", type text},
        {"correspondenceAddress", type text},
        {"SETTINGS_KS_REPORT_ENABLED", type logical}
    }),

    // --- Перевод на русский ---
    Наши_компании = Table.RenameColumns(Типизация, {
        {"__id", "ID компании"},
        {"__name", "Название"},
        {"__createdAt", "Дата создания"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedAt", "Дата изменения"},
        {"__updatedBy", "Кто изменил (ID)"},
        {"_inn", "ИНН"},
        {"_kpp", "КПП"},
        {"_ogrn", "ОГРН"},
        {"_full_legal_name", "Юр. наименование"},
        {"_legal_address", "Юр. адрес"},
        {"_actual_address", "Факт. адрес"},
        {"_bank", "Банк"},
        {"_bik", "БИК"},
        {"_transactional_account", "Расчётный счёт"},
        {"_correspondent_account", "Корр. счёт"},
        {"_phone", "Телефон"},
        {"_email", "Email"},
        {"web", "Сайт"},
        {"_director", "Директор (ID)"},
        {"signatory", "Подписант (ID)"},
        {"signatory_position", "Должность подписанта"},
        {"base_action", "Основание"},
        {"custom_okpo", "ОКПО"},
        {"correspondenceAddress", "Адрес для корреспонденции"},
        {"SETTINGS_KS_REPORT_ENABLED", "Отчёт КС включён"}
    })
in
    Наши_компании
