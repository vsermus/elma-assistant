import json

status_map = {
    1: 'Новый',
    3: 'В работе в ТЭО',
    4: 'Запрошена информация в ОС',
    6: 'Проигрыш тендера',
    7: 'Расчет выполнен',
    8: 'На понижении',
    9: 'Сформировано финальное КП',
    10: 'Финальное КП утверждено',
    11: 'Тендер выигран',
    12: 'Отказ от тендера',
    13: 'Подвести итоги тендера',
    14: 'Выход на тендер'
}

with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\data\raboty_po_tenderu.json', 'r', encoding='utf-8') as f:
    rpt = json.load(f)
items = rpt['result']['result']

with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\data\users.json', 'r', encoding='utf-8') as f:
    usr = json.load(f)
users = usr.get('result',{}).get('result',[])
um = {}
for u in users:
    um[u['__id']] = u

def format_user_name(uinfo):
    fn = uinfo.get('fullname', {})
    if isinstance(fn, dict):
        ln = fn.get('lastname','') or ''
        fn2 = fn.get('firstname','') or ''
        mn = fn.get('middlename','') or ''
        short_name = ln
        if fn2: short_name += ' ' + fn2[0] + '.'
        if mn: short_name += mn[0] + '.'
        return short_name
    return str(fn) if fn else ''

NO_TEO_LABEL = 'Не назначено'

teo = []
for r in items:
    if r.get('__deletedAt'): continue
    s = r.get('data_nachala_rabot_1')
    e = r.get('data_okonchaniya')
    if not s or not e: continue

    teo_ids = r.get('otvetstvennyi_v_teo', [])
    if teo_ids and len(teo_ids) > 0:
        uid = teo_ids[0] if isinstance(teo_ids, list) else teo_ids
        uinfo = um.get(uid, {})
        short_name = format_user_name(uinfo)
    else:
        uid = ''
        short_name = NO_TEO_LABEL

    st = r.get('__status')
    if isinstance(st, dict):
        status_code = st.get('status', 0)
    else:
        status_code = st if isinstance(st, int) else 0

    teo.append({
        'id': r['__id'],
        'name': r.get('__name',''),
        'start': s,
        'end': e,
        'user_id': uid,
        'user_name': short_name,
        'status': status_code,
        'status_name': status_map.get(status_code, 'Неизвестно'),
        'tender': r.get('tender', [''])[0] if isinstance(r.get('tender'), list) and r.get('tender') else '',
        'object': r.get('kratkoe_nazvanie_obekta',''),
        'comment_teo': r.get('kommentarii_sotrudniku_teo','') or '',
        'created': r.get('__createdAt','')
    })

json_str = json.dumps(teo, ensure_ascii=False)

# Generate status distribution
from collections import Counter
cnt = Counter(r['status_name'] for r in teo)
status_options = sorted(set(r['status_name'] for r in teo), key=lambda x: status_map.get({v:k for k,v in status_map.items()}.get(x, 99), 99))

# Colors per status
status_colors = {
    1: '#94a3b8',    # Новый - серый
    3: '#3b82f6',    # В работе в ТЭО - синий
    4: '#f59e0b',    # Запрошена информация в ОС - жёлтый
    6: '#ef4444',    # Проигрыш тендера - красный
    7: '#22c55e',    # Расчет выполнен - зелёный
    8: '#f97316',    # На понижении - оранжевый
    9: '#a855f7',    # Сформировано финальное КП - фиолетовый
    10: '#06b6d4',   # Финальное КП утверждено - голубой
    11: '#16a34a',   # Тендер выигран - тёмно-зелёный
    12: '#6b7280',   # Отказ от тендера - серый
    13: '#8b5cf6',   # Подвести итоги тендера - пурпурный
    14: '#14b8a6'    # Выход на тендер - бирюзовый
}

# Build HTML
html = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Загрузка ТЭО — Диаграмма Ганта</title>
<style>
:root {
  --primary: #2563eb;
  --primary-dark: #1d4ed8;
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --text-main: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --gantt-header-height: 40px;
  --row-label-width: 180px;
  --task-height: 18px;
  --task-gap: 3px;
  --multi-tag-gap: 4px;
}
.multi-select {
  position: relative;
  min-width: 220px;
}
.multi-select-trigger {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--multi-tag-gap);
  min-height: 36px;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
}
.multi-select-trigger.open {
  border-color: var(--primary);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}
.multi-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
}
.multi-tag-remove {
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  color: #94a3b8;
}
.multi-tag-remove:hover { color: #ef4444; }
.multi-placeholder {
  color: #94a3b8;
  padding: 2px 4px;
}
.multi-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid var(--primary);
  border-top: none;
  border-radius: 0 0 6px 6px;
  background: white;
  z-index: 100;
  box-shadow: var(--shadow);
}
.multi-dropdown.open { display: block; }
.multi-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.1s;
}
.multi-option:hover { background: #f1f5f9; }
.multi-option input[type="checkbox"] {
  margin: 0;
  accent-color: var(--primary);
}
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text-main);
  margin: 0;
  padding: 20px;
  line-height: 1.5;
}
.container { max-width: 1600px; margin: 0 auto; }
h1 { font-size: 24px; font-weight: 700; margin: 0 0 24px 0; color: var(--text-main); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.kpi-card {
  background: var(--card-bg);
  padding: 18px 20px;
  border-radius: 12px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}
.kpi-label { font-size: 13px; color: var(--text-muted); margin-bottom: 6px; }
.kpi-value { font-size: 26px; font-weight: 700; color: var(--primary); }
.kpi-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.filters-section {
  background: var(--card-bg);
  padding: 18px 20px;
  border-radius: 12px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  margin-bottom: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px 30px;
  align-items: end;
}
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.filter-group label { font-size: 13px; font-weight: 600; color: var(--text-muted); }
.dropdown {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  min-width: 200px;
  outline: none;
  background: white;
}
.date-input {
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}
.btn {
  padding: 8px 18px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn:hover { background: var(--primary-dark); }
.btn-outline {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
}
.btn-outline:hover { background: #f1f5f9; color: var(--text-main); }
.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 10px 16px;
  background: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border);
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}
.chart-section {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  margin-bottom: 24px;
  padding: 20px;
}
.chart-header h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: var(--text-main);
}
.chart-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  gap: 12px;
}
.chart-label {
  width: var(--row-label-width);
  min-width: var(--row-label-width);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
  text-align: right;
  padding-right: 8px;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chart-bars {
  flex: 1;
  display: flex;
  height: 28px;
  border-radius: 4px;
  overflow: hidden;
  background: #f1f5f9;
  position: relative;
}
.chart-bar-segment {
  height: 100%;
  transition: opacity 0.2s;
  cursor: pointer;
  position: relative;
}
.chart-bar-segment:hover {
  opacity: 0.8;
}
.chart-bar-segment .seg-tooltip {
  display: none;
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #1e293b;
  color: white;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
  pointer-events: none;
  margin-bottom: 4px;
}
.chart-bar-segment:hover .seg-tooltip {
  display: block;
}
.chart-total {
  min-width: 36px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  text-align: right;
}
.chart-scale {
  display: flex;
  justify-content: space-between;
  padding-left: calc(var(--row-label-width) + 12px);
  padding-right: 48px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}
.gantt-wrapper {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  overflow: hidden;
  margin-bottom: 24px;
  position: relative;
}
.gantt-header {
  display: flex;
  align-items: center;
  background: #f1f5f9;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  min-height: var(--gantt-header-height);
  position: sticky;
  top: 0;
  z-index: 2;
}
.gantt-header-label {
  width: var(--row-label-width);
  min-width: var(--row-label-width);
  padding: 0 16px;
  flex-shrink: 0;
}
.gantt-header-months {
  display: flex;
  flex: 1;
}
.gantt-month {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  border-left: 1px solid #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.gantt-body {
  position: relative;
}
.gantt-row {
  display: flex;
  border-bottom: 1px solid var(--border);
  position: relative;
}
.gantt-row-label {
  width: var(--row-label-width);
  min-width: var(--row-label-width);
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #fafbfc;
  border-right: 1px solid var(--border);
  box-sizing: border-box;
}
.user-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  margin-top: 2px;
}
.gantt-row-bars {
  flex: 1;
  position: relative;
  min-height: 60px;
  padding: 4px 0;
}
.gantt-bar {
  position: absolute;
  height: var(--task-height);
  border-radius: 3px;
  cursor: pointer;
  transition: opacity 0.15s, box-shadow 0.15s;
  min-width: 2px;
  box-sizing: border-box;
  border: 1px solid rgba(0,0,0,0.08);
}
.gantt-bar:hover {
  opacity: 0.85;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 5;
  height: 22px;
  margin-top: -2px;
}
.gantt-bar.dimmed { opacity: 0.15; }
.gantt-row-summary {
  position: absolute;
  right: 8px;
  top: 8px;
  font-size: 11px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.9);
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--border);
  pointer-events: none;
  z-index: 1;
}
.tooltip {
  position: fixed;
  background: #1e293b;
  color: white;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  pointer-events: none;
  z-index: 9999;
  max-width: 400px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  opacity: 0;
  transition: opacity 0.15s;
}
.tooltip.visible { opacity: 1; }
.tooltip .tt-name { font-weight: 600; font-size: 14px; margin-bottom: 6px; }
.tooltip .tt-row { display: flex; justify-content: space-between; gap: 16px; margin: 2px 0; }
.tooltip .tt-label { color: #94a3b8; }
.tooltip .tt-value { text-align: right; }
.tooltip .tt-comment { margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.15); color: #cbd5e1; font-size: 12px; }
.table-container {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  overflow: hidden;
}
.table-controls {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.search-input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  width: 280px;
  font-size: 14px;
  outline: none;
}
.search-input:focus { border-color: var(--primary); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  background: #f8fafc;
  padding: 10px 14px;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
  text-align: left;
}
th:hover { background: #f1f5f9; }
th .sort-icon { margin-left: 4px; font-size: 10px; }
td {
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
}
tr:hover { background: #f8fafc; }
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
@media (max-width: 768px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .filters-section { flex-direction: column; }
}
.gantt-month-grid {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: 1px solid var(--border);
  pointer-events: none;
}
.no-data {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
  font-size: 16px;
}
</style>
</head>
<body>
<div class="container">
  <h1>Загрузка ТЭО — Диаграмма Ганта</h1>
  <div class="kpi-grid" id="kpi-grid"></div>
  <div class="filters-section">
    <div class="filter-group">
      <label>Сотрудник</label>
      <div class="multi-select" id="ms-user">
        <div class="multi-select-trigger" onclick="toggleMulti('user')">
          <span class="multi-placeholder" id="ms-user-placeholder">Все сотрудники</span>
        </div>
        <div class="multi-dropdown" id="ms-user-dd"></div>
      </div>
    </div>
    <div class="filter-group">
      <label>Статус</label>
      <div class="multi-select" id="ms-status">
        <div class="multi-select-trigger" onclick="toggleMulti('status')">
          <span class="multi-placeholder" id="ms-status-placeholder">Все статусы</span>
        </div>
        <div class="multi-dropdown" id="ms-status-dd"></div>
      </div>
    </div>
    <div class="filter-group">
      <label>Дата от</label>
      <input type="date" class="date-input" id="filter-date-from">
    </div>
    <div class="filter-group">
      <label>Дата до</label>
      <input type="date" class="date-input" id="filter-date-to">
    </div>
    <button class="btn" onclick="applyFilters()">Применить</button>
    <button class="btn btn-outline" onclick="resetFilters()">Сбросить</button>
  </div>

  <div class="legend" id="legend">
'''

for code, name in sorted(status_map.items(), key=lambda x: x[1]):
    color = status_colors.get(code, '#94a3b8')
    html += f'    <div class="legend-item"><div class="legend-color" style="background:{color}"></div>{name}</div>\n'

html += '''  </div>

  <!-- Summary Chart: tasks per employee by status -->
  <div class="chart-section">
    <div class="chart-header">
      <h2>Распределение задач по сотрудникам и статусам</h2>
    </div>
    <div id="summary-chart"></div>
  </div>

  <div class="gantt-wrapper" id="gantt-wrapper">
    <div id="gantt-container"></div>
  </div>

  <div class="table-container">
    <div class="table-controls">
      <input type="text" class="search-input" id="search" placeholder="Поиск по задачам, объектам...">
      <div style="font-size:13px;color:var(--text-muted)" id="table-info">Всего записей: 0</div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th onclick="sortTable('name')">Задача <span class="sort-icon">▼</span></th>
            <th onclick="sortTable('user_name')">Сотрудник <span class="sort-icon"></span></th>
            <th onclick="sortTable('object')">Объект <span class="sort-icon"></span></th>
            <th onclick="sortTable('status_name')">Статус <span class="sort-icon"></span></th>
            <th onclick="sortTable('start')">Дата старта <span class="sort-icon"></span></th>
            <th onclick="sortTable('end')">Дата окончания <span class="sort-icon"></span></th>
            <th onclick="sortTable('duration')">Длительность <span class="sort-icon"></span></th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
    </div>
  </div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
const ganttData = ''' + json_str + ''';

const state = {
  data: [],
  filtered: [],
  sortField: 'start',
  sortDir: 'asc',
  userFilter: [],
  statusFilter: [],
  dateFrom: null,
  dateTo: null,
  search: ''
};

const STATUS_COLORS = ''' + json.dumps({str(k): v for k, v in status_colors.items()}, ensure_ascii=False) + ''';
const statusNames = ''' + json.dumps({k: v for k, v in status_map.items()}, ensure_ascii=False) + ''';

'''

with open(r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\dashboards\загрузка_тэо_гант.html', 'w', encoding='utf-8') as f:
    f.write(html)

from collections import Counter
cnt = Counter(r['user_name'] for r in teo)
print('Done! Size:', len(html), 'bytes, Records:', len(teo))
for n, c in cnt.most_common():
    print(f'  {n}: {c}')
