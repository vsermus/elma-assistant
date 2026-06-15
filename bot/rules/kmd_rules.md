# Правила для КМД агента

## Связи КМД-сущностей
- zadanie_na_kmd.id_proekta → spravochnik_id.__id
- kartochka_vitrazha_po_km.id_proekta → spravochnik_id.__id
- kartochka_vitrazha_po_km.zadanie_na_kmd_2025 → zadanie_na_kmd.__id
- order_by_kmd.id_proekta → spravochnik_id.__id
- order_by_kmd.zadanie_na_kmd_2025 → zadanie_na_kmd.__id
- zns_po_kmd.order_by_kmd → order_by_kmd.__id
- zns_po_kmd.id_proekta → spravochnik_id.__id
- zns_po_kmd.supplier_company → _companies.__id
- ozm.id_proekta_1 → spravochnik_id.__id
- ozm.kartochki_vitrazhei_po_km → kartochka_vitrazha_po_km.__id

## Ключевые поля для ответов
- Статус задания: __status.status → lookup в статусах
- Просрочка: plan_date_rop vs факт
- Площадь: kartochka_vitrazha_po_km.ploshad_m2
- Даты поставок: zns_po_kmd.plan_plant_date, zns_po_kmd.fact_plant_date
