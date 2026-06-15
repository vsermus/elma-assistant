// ========================================================
// РАСПОЗНАННЫЕ ДОКУМЕНТЫ (УПД / Счет-фактура) — загрузка из ELMA365 в Power BI
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- HTTP GET ---
    Ответ = Json.Document(
        Web.Contents("https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/correct_recognition/ptiu_documents/list?query={""size"": 10000}", [
            Headers = [
                Authorization = "Bearer 2ad06f66-6ecc-42b3-9bf4-1ef21eabb371",
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

    // --- Фильтр удалённых записей ---
    БезУдалённых = Table.SelectRows(Таблица, each ([__deletedAt] = null)),

    // --- docType: список {code, name} → первое name ---
    ИзвлечьТипДок = Table.TransformColumns(
        БезУдалённых,
        {"docType",
            each if _ is list and List.Count(_) > 0 then _{0}[name] else null, type text}
    ),

    // --- id_proekta_extended: список ID → первый ---
    ИзвлечьОбъект = Table.TransformColumns(
        ИзвлечьТипДок,
        {"id_proekta_extended",
            each if _ is list and List.Count(_) > 0 then _{0} else null, type text}
    ),

    // --- Авторы: text или list → text ---
    ИзвлечьАвторов = Table.TransformColumns(
        ИзвлечьОбъект, {
            {"__createdBy",
                each if _ is list and List.Count(_) > 0 then _{0} else if _ is text then _ else null, type text},
            {"__updatedBy",
                each if _ is list and List.Count(_) > 0 then _{0} else if _ is text then _ else null, type text}
        }
    ),

    // --- Суммы: {cents, currency} → рубли ---
    ИзвлечьСуммы = Table.TransformColumns(
        ИзвлечьАвторов, {
            {"sumWithVat",
                each if _ is record then _[cents] / 100 else null, type number},
            {"sumWithoutVat",
                each if _ is record then _[cents] / 100 else null, type number},
            {"vatSum",
                each if _ is record then _[cents] / 100 else null, type number}
        }
    ),

    // --- Выбор колонок ---
    ВыборКолонок = Table.SelectColumns(ИзвлечьСуммы, {
        "__id", "__name",
        "docType", "docNumber", "docDate",
        "supplierName", "supplierInn",
        "customerName", "customerInn",
        "sumWithVat", "sumWithoutVat", "vatSum",
        "contractNumber", "contractDate",
        "id_proekta_extended",
        "__createdAt", "__updatedAt", "__createdBy", "__updatedBy"
    }, MissingField.UseNull),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(ВыборКолонок, {
        {"__id", type text},
        {"__name", type text},
        {"docType", type text},
        {"docNumber", type text},
        {"docDate", type datetimezone},
        {"supplierName", type text},
        {"supplierInn", type text},
        {"customerName", type text},
        {"customerInn", type text},
        {"sumWithVat", type number},
        {"sumWithoutVat", type number},
        {"vatSum", type number},
        {"contractNumber", type text},
        {"contractDate", type datetimezone},
        {"id_proekta_extended", type text},
        {"__createdAt", type datetimezone},
        {"__updatedAt", type datetimezone},
        {"__createdBy", type text},
        {"__updatedBy", type text}
    }),

    // --- Дата без времени ---
    ДатаБезВремени = Table.TransformColumns(Типизация, {
        {"docDate", Date.From, type date},
        {"contractDate", Date.From, type date},
        {"__createdAt", Date.From, type date},
        {"__updatedAt", Date.From, type date}
    }),

    // --- Ссылка на запись в ELMA ---
    СоСсылкой = Table.AddColumn(
        ДатаБезВремени,
        "Линк",
        each "https://dlqixw6ehyxiy.elma365.ru/construction/receipt_tmc(p:item/correct_recognition/ptiu_documents/" & [__id] & ")",
        type text
    ),

    // --- Перевод на русский ---
    Документы = Table.RenameColumns(СоСсылкой, {
        {"__id", "ID документа"},
        {"__name", "Название"},
        {"docType", "Тип документа"},
        {"docNumber", "Номер документа"},
        {"docDate", "Дата документа"},
        {"supplierName", "Поставщик"},
        {"supplierInn", "ИНН поставщика"},
        {"customerName", "Покупатель"},
        {"customerInn", "ИНН покупателя"},
        {"sumWithVat", "Сумма с НДС, руб"},
        {"sumWithoutVat", "Сумма без НДС, руб"},
        {"vatSum", "НДС, руб"},
        {"contractNumber", "Номер договора"},
        {"contractDate", "Дата договора"},
        {"id_proekta_extended", "ID объекта"},
        {"__createdAt", "Дата создания"},
        {"__updatedAt", "Дата изменения"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedBy", "Изменивший (ID)"}
    })

in
    Документы
