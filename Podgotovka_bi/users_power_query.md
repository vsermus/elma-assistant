// ========================================================
// ПОЛЬЗОВАТЕЛИ — загрузка данных из ELMA365 в Power BI
// ========================================================
// 1. Замените "ВАШ_ТОКЕН" на значение ELMA_TOKEN из .env
// 2. Power BI: Главная → Получить данные → Другие → Пустой запрос
// 3. Откройте расширенный редактор и вставьте этот код
// ========================================================

let
    // --- Параметры ---
    БазовыйURL = "https://dlqixw6ehyxiy.elma365.ru/pub/v1/user/list",
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
        "__createdAt", "__updatedAt",
        "fullname", "login", "email",
        "displayedPosition", "mobilePhone",
        "birthDate", "hireDate", "timezone"
    }),

    // --- fullname: {firstname, lastname, middlename} → Фамилия И.О. ---
    ИзвлечьФИО = Table.TransformColumns(
        ВыборКолонок,
        {"fullname",
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

    // --- mobilePhone: тел. список → первый номер ---
    ИзвлечьТелефон = Table.TransformColumns(
        ИзвлечьФИО,
        {"mobilePhone",
            each
                if _ is list and List.Count(_) > 0
                then _{0}[tel]
                else null,
            type text}
    ),

    // --- Удаляем полностью пустые колонки ---
    УдалитьПустые = Table.SelectColumns(
        ИзвлечьТелефон,
        List.Select(
            Table.ColumnNames(ИзвлечьТелефон),
            each List.NonNullCount(Table.Column(ИзвлечьТелефон, _)) > 0
        )
    ),

    // --- Типизация ---
    Типизация = Table.TransformColumnTypes(УдалитьПустые, {
        {"__id", type text},
        {"__name", type text},
        {"__createdAt", type datetimezone},
        {"__updatedAt", type datetimezone},
        {"fullname", type text},
        {"login", type text},
        {"email", type text},
        {"displayedPosition", type text},
        {"mobilePhone", type text},
        {"birthDate", type datetimezone},
        {"hireDate", type datetimezone},
        {"timezone", type text}
    }),

    // --- Перевод на русский ---
    ДатаБезВремени = Table.TransformColumns(Типизация, {
        {"birthDate", Date.From, type date},
        {"hireDate", Date.From, type date}
    }),

    Пользователи = Table.RenameColumns(ДатаБезВремени, {
        {"__id", "ID пользователя"},
        {"__name", "Отображаемое имя"},
        {"__createdAt", "Дата создания"},
        {"__updatedAt", "Дата изменения"},
        {"fullname", "ФИО"},
        {"login", "Логин"},
        {"email", "Email"},
        {"displayedPosition", "Должность"},
        {"mobilePhone", "Телефон"},
        {"birthDate", "Дата рождения"},
        {"hireDate", "Дата приёма"},
        {"timezone", "Часовой пояс"}
    })
in
    Пользователи
