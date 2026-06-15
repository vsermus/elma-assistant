# Правила для Тендерного агента

## Связи тендерных сущностей
- raboty_po_tenderu.tender → tender.__id
- raboty_po_tenderu.id_proekta_1 → spravochnik_id.__id
- tender.id_proekta_1 → spravochnik_id.__id
- tender.zakazchik → _companies.__id
- raboty_po_tenderu.zakazchik → _companies.__id
- raboty_po_tenderu.__status.status → statusy_rabot_po_tenderam.id

## Ключевые поля для ответов
- Статус тендера: __status (числовой код)
- Типы работ: tipy_rabot (массив)
- Площадь: kvadratura
- Сумма: summa_dogovora / summa_kvadraty
- Ответственные: rukovoditel_proekta, iniciator_rabot_1 → users.__id
