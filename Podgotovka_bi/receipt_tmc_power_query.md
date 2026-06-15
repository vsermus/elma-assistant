// ========================================================
// ПРИЁМКА ТМЦ — загрузка данных из ELMA365 в Power BI
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

    // --- __status: {order, status} → текст статуса ---
    ИзвлечьСтатус = Table.TransformColumns(
        БезУдалённых,
        {"__status",
            each
                let код = if _ is record then _[status] else null
                in if код = 1 then "Новая"
                   else if код = 2 then "Обработана"
                   else null,
            type text}
    ),

    // --- id_proekta: список ID → первый ---
    ИзвлечьСсылки = Table.TransformColumns(
        ИзвлечьСтатус, {
            {"id_proekta",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"otvetstvennyi",
                each if _ is list and List.Count(_) > 0 then _{0} else null, type text},
            {"__createdBy",
                each if _ is list and List.Count(_) > 0 then _{0} else if _ is text then _ else null, type text},
            {"__updatedBy",
                each if _ is list and List.Count(_) > 0 then _{0} else if _ is text then _ else null, type text}
        }
    ),

    // --- tip_postavki, sostoyanie_postavki: список {code, name} → первое name ---
    ИзвлечьСписки = Table.TransformColumns(
        ИзвлечьСсылки, {
            {"tip_postavki",
                each if _ is list and List.Count(_) > 0 then _{0}[name] else null, type text},
            {"sostoyanie_postavki",
                each if _ is list and List.Count(_) > 0 then _{0}[name] else null, type text}
        }
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(ИзвлечьСписки, {
        {"__id", type text},
        {"__name", type text},
        {"__status", type text},
        {"__index", Int64.Type},
        {"__version", Int64.Type},
        {"__createdAt", type datetimezone},
        {"__createdBy", type text},
        {"__updatedAt", type datetimezone},
        {"__updatedBy", type text},
        {"itogovyi_id", type text},
        {"idp4s", type text},
        {"id_proekta", type text},
        {"tip_postavki", type text},
        {"sostoyanie_postavki", type text},
        {"brak", type logical},
        {"comment", type text},
        {"otvetstvennyi", type text}
    }),

    // --- Дата без времени ---
    ДатаБезВремени = Table.TransformColumns(Типизация, {
        {"__createdAt", Date.From, type date},
        {"__updatedAt", Date.From, type date}
    }),

    // --- Ссылка на запись в ELMA ---
    СоСсылкой = Table.AddColumn(
        ДатаБезВремени,
        "Линк",
        each "https://dlqixw6ehyxiy.elma365.ru/construction/receipt_tmc(p:item/construction/receipt_tmc/" & [__id] & ")",
        type text
    ),

    // --- Выбор и порядок колонок ---
    ВыборКолонок = Table.SelectColumns(СоСсылкой, {
        "__id", "__name", "itogovyi_id", "id_proekta", "idp4s",
        "__status", "tip_postavki", "sostoyanie_postavki", "brak", "comment",
        "otvetstvennyi", "__createdAt", "__updatedAt", "__createdBy", "__updatedBy",
        "Линк"
    }, MissingField.UseNull),

    // --- Перевод на русский ---
    Приёмка_ТМЦ = Table.RenameColumns(ВыборКолонок, {
        {"__id", "ID записи"},
        {"__name", "Название"},
        {"itogovyi_id", "Итоговый ID объекта"},
        {"id_proekta", "ID объекта"},
        {"idp4s", "IDP4S"},
        {"__status", "Статус"},
        {"tip_postavki", "Тип поставки"},
        {"sostoyanie_postavki", "Состояние комплектации"},
        {"brak", "Брак"},
        {"comment", "Комментарий"},
        {"otvetstvennyi", "Ответственный (ID)"},
        {"__createdAt", "Дата создания"},
        {"__updatedAt", "Дата изменения"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedBy", "Изменивший (ID)"}
    })

in
    Приёмка_ТМЦ
