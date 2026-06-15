// ========================================================
// ЖУРНАЛ РАБОТ — загрузка данных из ELMA365 в Power BI
// ========================================================
// Power BI: Главная → Получить данные → Другие → Пустой запрос
// Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- HTTP GET ---
    Ответ = Json.Document(
        Web.Contents("https://dlqixw6ehyxiy.elma365.ru/pub/v1/app/construction/jobs_journal/list?query={""size"": 10000}", [
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

    // --- Выбор колонок ---
    ВыборКолонок = Table.SelectColumns(БезУдалённых, {
        "__id", "__name", "__status",
        "__createdAt", "__createdBy", "__updatedAt", "__updatedBy",
        "plan_fact_switch", "journal_status", "linked_plan_id",
        "id_proekta", "rp", "otvetstvennyi", "sender_fio",
        "vid_rabot", "pbi_vid_rabot",
        "etap_mokryi_fasad", "etap_nvf", "etap_kholodnye_vitrazhi", "etap_tyoplye_vitrazhi",
        "pbi_etap_mokryi_fasad", "pbi_etap_nvf", "pbi_etap_kholodnye_vitrazhi", "pbi_etap_tyoplye_vitrazhi",
        "korpus", "section", "zakhvatka",
        "pbi_korpus", "pbi_section", "pbi_zakhvatka",
        "obem", "pbi_obem", "stoimost",
        "kolichestvo_ispolnitelei", "pbi_kolichestvo_ispolnitelei",
        "data_nachala_rabot", "data_okonchaniya_rabot",
        "zadacha", "comment", "kommentarii",
        "kategoriya_rabot", "tekhnika"
    }, MissingField.UseNull),

    // --- __status → число ---
    ИзвлечьСтатус = Table.TransformColumns(
        ВыборКолонок,
        {"__status", each if _ is record then _[status] else null, Int64.Type}
    ),

    // --- Списки-ссылки: первый ID ---
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

    // --- Записи {code, name} → name ---
    ИзвлечьЗаписи = Table.TransformColumns(
        ИзвлечьСсылки, {
            {"vid_rabot",
                each if _ is record then _[name] else null, type text},
            {"etap_mokryi_fasad",
                each if _ is record then _[name] else null, type text},
            {"etap_nvf",
                each if _ is record then _[name] else null, type text},
            {"etap_kholodnye_vitrazhi",
                each if _ is record then _[name] else null, type text},
            {"etap_tyoplye_vitrazhi",
                each if _ is record then _[name] else null, type text},
            {"korpus",
                each if _ is record then _[name] else null, type text},
            {"section",
                each if _ is record then _[name] else null, type text}
        }
    ),

    // --- kategoriya_rabot, tekhnika: список {code, name} → текст через "; " ---
    ИзвлечьСписки = Table.TransformColumns(
        ИзвлечьЗаписи, {
            {"kategoriya_rabot",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text},
            {"tekhnika",
                each if _ is list and List.Count(_) > 0
                    then Text.Combine(List.Transform(_, each _[name]), "; ")
                    else null, type text}
        }
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(ИзвлечьСписки, {
        {"__id", type text},
        {"__name", type text},
        {"__status", Int64.Type},
        {"__createdAt", type datetimezone},
        {"__createdBy", type text},
        {"__updatedAt", type datetimezone},
        {"__updatedBy", type text},
        {"plan_fact_switch", type logical},
        {"journal_status", type text},
        {"linked_plan_id", type text},
        {"id_proekta", type text},
        {"rp", type text},
        {"otvetstvennyi", type text},
        {"sender_fio", type text},
        {"vid_rabot", type text},
        {"pbi_vid_rabot", type text},
        {"etap_mokryi_fasad", type text},
        {"etap_nvf", type text},
        {"etap_kholodnye_vitrazhi", type text},
        {"etap_tyoplye_vitrazhi", type text},
        {"pbi_etap_mokryi_fasad", type text},
        {"pbi_etap_nvf", type text},
        {"pbi_etap_kholodnye_vitrazhi", type text},
        {"pbi_etap_tyoplye_vitrazhi", type text},
        {"korpus", type text},
        {"section", type text},
        {"zakhvatka", type text},
        {"pbi_korpus", type text},
        {"pbi_section", type text},
        {"pbi_zakhvatka", type text},
        {"obem", type number},
        {"pbi_obem", type number},
        {"stoimost", type number},
        {"kolichestvo_ispolnitelei", Int64.Type},
        {"pbi_kolichestvo_ispolnitelei", Int64.Type},
        {"data_nachala_rabot", type datetimezone},
        {"data_okonchaniya_rabot", type datetimezone},
        {"zadacha", type text},
        {"comment", type text},
        {"kommentarii", type text},
        {"kategoriya_rabot", type text},
        {"tekhnika", type text}
    }),

    // --- Дата без времени ---
    ДатаБезВремени = Table.TransformColumns(Типизация, {
        {"__createdAt", Date.From, type date},
        {"__updatedAt", Date.From, type date},
        {"data_nachala_rabot", Date.From, type date},
        {"data_okonchaniya_rabot", Date.From, type date}
    }),

    // --- Ссылка на запись в ELMA ---
    СоСсылкой = Table.AddColumn(
        ДатаБезВремени,
        "Линк",
        each "https://dlqixw6ehyxiy.elma365.ru/construction/jobs_journal(p:item/construction/jobs_journal/" & [__id] & ")",
        type text
    ),

    // --- Перевод на русский ---
    Журнал_работ = Table.RenameColumns(СоСсылкой, {
        {"__id", "ID записи"},
        {"__name", "Название"},
        {"__status", "Код статуса"},
        {"__createdAt", "Дата создания"},
        {"__createdBy", "Создатель (ID)"},
        {"__updatedAt", "Дата изменения"},
        {"__updatedBy", "Изменивший (ID)"},
        {"plan_fact_switch", "Факт"},
        {"journal_status", "Статус журнала"},
        {"linked_plan_id", "ID связанного плана"},
        {"id_proekta", "ID объекта"},
        {"rp", "РП (ID)"},
        {"otvetstvennyi", "Ответственный (ID)"},
        {"sender_fio", "ФИО отправителя"},
        {"vid_rabot", "Вид работ"},
        {"pbi_vid_rabot", "Вид работ (PBI)"},
        {"etap_mokryi_fasad", "Этап МФ"},
        {"etap_nvf", "Этап НВФ"},
        {"etap_kholodnye_vitrazhi", "Этап ВХ"},
        {"etap_tyoplye_vitrazhi", "Этап ВТ"},
        {"pbi_etap_mokryi_fasad", "Этапы МФ (PBI)"},
        {"pbi_etap_nvf", "Этапы НВФ (PBI)"},
        {"pbi_etap_kholodnye_vitrazhi", "Этапы ВХ (PBI)"},
        {"pbi_etap_tyoplye_vitrazhi", "Этапы ВТ (PBI)"},
        {"korpus", "Корпус"},
        {"section", "Секция"},
        {"zakhvatka", "Захватка"},
        {"pbi_korpus", "Корпуса (PBI)"},
        {"pbi_section", "Секции (PBI)"},
        {"pbi_zakhvatka", "Захватки (PBI)"},
        {"obem", "Объём"},
        {"pbi_obem", "Объём (PBI)"},
        {"stoimost", "Стоимость"},
        {"kolichestvo_ispolnitelei", "Кол-во исполнителей"},
        {"pbi_kolichestvo_ispolnitelei", "Кол-во исполнителей (PBI)"},
        {"data_nachala_rabot", "Дата начала"},
        {"data_okonchaniya_rabot", "Дата окончания"},
        {"zadacha", "Задача"},
        {"comment", "Комментарий"},
        {"kommentarii", "Комментарии"},
        {"kategoriya_rabot", "Категория работ"},
        {"tekhnika", "Техника"}
    }, MissingField.UseNull)
in
    Журнал_работ
