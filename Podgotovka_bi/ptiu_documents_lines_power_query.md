// ========================================================
// ПОЗИЦИИ ДОКУМЕНТОВ (табличная часть УПД / Счет-фактура) — загрузка из ELMA365 в Power BI
// ========================================================
// Разворачивает строки табличной части из каждого распознанного документа.
// Используется как детализация к таблице документов:
//   Документы  ──[ID документа]──→  Позиции документов
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

    // --- Оставляем только ID документа + табличная часть ---
    ТолькоТаблица = Table.SelectColumns(БезУдалённых, {"__id", "table"}, MissingField.UseNull),

    // --- Извлекаем rows из table ---
    ИзвлечьСтроки = Table.TransformColumns(
        ТолькоТаблица,
        {"table",
            each if _ is record and _[rows] <> null then _[rows] else {}, Value.Type({})}
    ),

    // --- Разворачиваем список строк ---
    Развернуть = Table.ExpandListColumn(ИзвлечьСтроки, "table"),

    // --- Убираем пустые строки ---
    БезПустых = Table.SelectRows(Развернуть, each [table] <> null),

    // --- Разворачиваем поля каждой строки ---
    РазвернутьПоля = Table.ExpandRecordColumn(
        БезПустых,
        "table",
        {"name", "article", "quantity", "unitName", "vatRate",
         "price", "sumWithVat", "sumWithoutVat", "vatSum",
         "countryName", "declarationNumber"},
        {"name", "article", "quantity", "unitName", "vatRate",
         "price", "sumWithVat", "sumWithoutVat", "vatSum",
         "countryName", "declarationNumber"}
    ),

    // --- Суммы: {cents, currency} → рубли ---
    ИзвлечьСуммы = Table.TransformColumns(
        РазвернутьПоля, {
            {"price",
                each if _ is record then _[cents] / 100 else null, type number},
            {"sumWithVat",
                each if _ is record then _[cents] / 100 else null, type number},
            {"sumWithoutVat",
                each if _ is record then _[cents] / 100 else null, type number},
            {"vatSum",
                each if _ is record then _[cents] / 100 else null, type number}
        }
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(ИзвлечьСуммы, {
        {"__id", type text},
        {"name", type text},
        {"article", type text},
        {"quantity", type number},
        {"unitName", type text},
        {"vatRate", type number},
        {"price", type number},
        {"sumWithVat", type number},
        {"sumWithoutVat", type number},
        {"vatSum", type number},
        {"countryName", type text},
        {"declarationNumber", type text}
    }),

    // --- Перевод на русский ---
    Позиции = Table.RenameColumns(Типизация, {
        {"__id", "ID документа"},
        {"name", "Наименование"},
        {"article", "Артикул"},
        {"quantity", "Количество"},
        {"unitName", "Единица"},
        {"vatRate", "Ставка НДС, %"},
        {"price", "Цена за ед., руб"},
        {"sumWithVat", "Сумма с НДС, руб"},
        {"sumWithoutVat", "Сумма без НДС, руб"},
        {"vatSum", "НДС, руб"},
        {"countryName", "Страна происхождения"},
        {"declarationNumber", "Номер декларации"}
    })

in
    Позиции
