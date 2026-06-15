// ========================================================
// СВЯЗИ: ПРИЁМКА ТМЦ ↔ ДОКУМЕНТЫ — промежуточная таблица для Power BI
// ========================================================
// Разворачивает лог распознавания из каждой приёмки ТМЦ.
// Используется как мост между таблицами:
//   Приёмка_ТМЦ  ──→  Связи  ──→  Документы
// В Power BI: Моделирование → Управление связями → добавить обе связи.
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- HTTP GET ---
    Ответ = Json.Document(
        Web.Contents("https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/construction/receipt_tmc/list?query={""size"": 10000}", [
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

    // --- Оставляем только нужные колонки: ID приёмки + лог ---
    ТолькоЛог = Table.SelectColumns(БезУдалённых, {"__id", "recognition_log_table"}, MissingField.UseNull),

    // --- Извлекаем rows из recognition_log_table ---
    ИзвлечьСтроки = Table.TransformColumns(
        ТолькоЛог,
        {"recognition_log_table",
            each if _ is record and _[rows] <> null then _[rows] else {}, Value.Type({})}
    ),

    // --- Разворачиваем список строк в отдельные записи ---
    Развернуть = Table.ExpandListColumn(ИзвлечьСтроки, "recognition_log_table"),

    // --- Убираем строки без данных ---
    БезПустых = Table.SelectRows(Развернуть, each [recognition_log_table] <> null),

    // --- Разворачиваем поля каждой строки лога ---
    РазвернутьПоля = Table.ExpandRecordColumn(
        БезПустых,
        "recognition_log_table",
        {"doc_link", "doc_type", "file_name", "is_recognized"},
        {"doc_link", "doc_type", "file_name", "is_recognized"}
    ),

    // --- doc_link: список ID → первый (ID документа ptiu_documents) ---
    ИзвлечьID = Table.TransformColumns(
        РазвернутьПоля,
        {"doc_link",
            each if _ is list and List.Count(_) > 0 then _{0} else null, type text}
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(ИзвлечьID, {
        {"__id", type text},
        {"doc_link", type text},
        {"doc_type", type text},
        {"file_name", type text},
        {"is_recognized", type logical}
    }),

    // --- Перевод на русский ---
    Связи = Table.RenameColumns(Типизация, {
        {"__id", "ID приёмки"},
        {"doc_link", "ID документа"},
        {"doc_type", "Тип документа"},
        {"file_name", "Имя файла"},
        {"is_recognized", "Распознан"}
    })

in
    Связи
