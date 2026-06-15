// ========================================================
// КАЛЕНДАРЬ — таблица дат для мер (DAX, вычисляемая таблица)
// ========================================================
// Power BI: Моделирование → Создать таблицу → вставить код
// ========================================================

Календарь =
VAR MinDate = MIN(
    MINX('Тендеры', 'Тендеры'[Начало тендера]),
    MINX('Работы_по_тендеру', 'Работы_по_тендеру'[Начало работ])
)
VAR MaxDate = MAX(
    MAXX('Тендеры', 'Тендеры'[Окончание стр-ва]),
    MAXX('Работы_по_тендеру', 'Работы_по_тендеру'[Окончание работ])
)
VAR StartDate = DATE(YEAR(MinDate) - 1, 1, 1)
VAR EndDate = DATE(YEAR(MaxDate) + 1, 12, 31)
RETURN
    ADDCOLUMNS(
        CALENDAR(StartDate, EndDate),
        "Год", YEAR([Date]),
        "Квартал", QUARTER([Date]),
        "Месяц", MONTH([Date]),
        "Название месяца", FORMAT([Date], "MMMM"),
        "Месяц год", FORMAT([Date], "YYYY MMMM"),
        "Номер недели", WEEKNUM([Date], 2),
        "День", DAY([Date]),
        "День года", DATEDIFF(DATE(YEAR([Date]), 1, 1), [Date], DAY) + 1,
        "День недели", WEEKDAY([Date], 2),
        "Название дня", FORMAT([Date], "dddd"),
        "Рабочий день", IF(WEEKDAY([Date], 2) < 6, TRUE, FALSE),
        "Год-квартал", YEAR([Date]) & "-КВ" & QUARTER([Date]),
        "Год-месяц", YEAR([Date]) * 100 + MONTH([Date])
    )
