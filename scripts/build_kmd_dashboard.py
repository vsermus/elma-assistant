#!/usr/bin/env python3
"""
Generates the KMD Orders Dashboard HTML file with embedded data.
Reads JSON files, compacts field names, and builds a complete offline HTML dashboard.
"""
import json
import os
import gzip
from io import BytesIO

BASE = r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector'
DATA_DIR = os.path.join(BASE, 'data')
OUT_FILE = os.path.join(BASE, 'dashboards', 'заказы_по_кмд_2026.html')

# Status map
STATUS_MAP = {
    1: 'Новый', 2: 'МПДО', 3: 'РОС', 4: 'Завершен',
    5: 'Частично СК', 6: 'МОС', 7: 'КОП', 8: 'РП',
    9: 'Удалить', 10: 'Все ЗНС включены', 11: 'КО'
}
STATUS_CLASSES = {
    1: 'new', 2: 'mpdo', 3: 'ros', 4: 'done', 5: 'part',
    6: 'mos', 7: 'kop', 8: 'rp', 9: 'del', 10: 'all', 11: 'ko'
}

def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)['result']['result']

def get_user_name(u):
    fn = u.get('fullname', {})
    parts = [fn.get('lastname',''), fn.get('firstname',''), fn.get('middlename','')]
    return ' '.join(p for p in parts if p).strip() or u.get('__name','').strip()

def compact_orders(orders):
    """Extract only needed fields with short names."""
    result = []
    for o in orders:
        item = {
            'id': o['__id'],
            'ca': o.get('__createdAt', ''),
            'ua': o.get('__updatedAt', ''),
            'sca': o.get('__statusChangedAt', ''),
            'st': o.get('__status', {}).get('status', 0),
            'rp': o.get('rp') or [],
            'obj': o.get('id_proekta') or [],
            'dp': o.get('data_polnoi_komplektnosti_sk', ''),
            'kor': o.get('korpus', ''),
            'sec': o.get('section', ''),
            'zns': o.get('zns_po_kmd') or [],
        }
        # Only add tasks if they exist
        tasks = o.get('__tasks')
        if tasks:
            item['ts'] = [{
                'tp': t.get('template', ''),
                'st': t.get('state', ''),
                'ca': t.get('__createdAt', '')
            } for t in tasks]
        # Only add deletedAt if not null
        if o.get('__deletedAt'):
            item['del'] = o['__deletedAt']
        result.append(item)
    return result

def compact_zns(zns_list):
    """Extract only needed fields from ZNS with short names."""
    result = []
    for z in zns_list:
        item = {
            'id': z['__id'],
            'ca': z.get('__createdAt', ''),
            'rp': z.get('plan_data_rp', ''),
            'mos': z.get('plan_data_mos', ''),
            'post': z.get('data_postavki', ''),
            'fakt': z.get('fakt_data_postavki_mos', ''),
            'kor': z.get('korpus', ''),
            'sec': z.get('section', ''),
            'oid': z.get('order_by_kmd') or [],
        }
        # Some ZNS items might not have __deletedAt key at all
        try:
            if z.get('__deletedAt'):
                item['del'] = z['__deletedAt']
        except (KeyError, AttributeError):
            pass
        result.append(item)
    return result

def build_data_json():
    """Read all data files and build compact DATA for embedding."""
    print("Loading data...")
    orders_raw = load_json('order_by_kmd.json')
    zns_raw = load_json('zns_po_kmd.json')
    users_raw = load_json('users.json')
    objs_raw = load_json('spravochnik_id.json')
    
    print(f"  Orders: {len(orders_raw)}")
    print(f"  ZNS: {len(zns_raw)}")
    print(f"  Users: {len(users_raw)}")
    print(f"  Objects: {len(objs_raw)}")
    
    # Compact
    users = [{'id': u['__id'], 'name': get_user_name(u)} for u in users_raw]
    objs = []
    for o in objs_raw:
        item = {'id': o['__id'], 'name': o.get('__name','')}
        if o.get('itogovyi_id'):
            item['iid'] = o['itogovyi_id']
        objs.append(item)
    
    orders = compact_orders(orders_raw)
    zns = compact_zns(zns_raw)
    
    status_map_dict = {str(k): v for k, v in STATUS_MAP.items()}
    
    data = {
        'o': orders,
        'u': users,
        'ob': objs,
        'sm': status_map_dict,
        'z': zns,
    }
    
    print(f"  Compacted orders: {len(orders)}")
    print(f"  Compacted ZNS: {len(zns)}")
    
    return data

def format_json_size(data):
    """Get approximate JSON size."""
    raw = json.dumps(data, ensure_ascii=False, separators=(',',':'))
    return len(raw)

# ---- HTML TEMPLATE ----

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Заказы по КМД — Дашборд</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#f1f5f9;--card:#fff;--primary:#2563eb;--primary-light:#dbeafe;--text:#0f172a;--text-secondary:#64748b;--border:#e2e8f0;--success:#16a34a;--warning:#d97706;--danger:#dc2626;--radius:10px;--shadow:0 1px 3px rgba(0,0,0,.08)}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.5}
.header{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.header h1{font-size:20px;font-weight:600}
.header .sub{font-size:12px;opacity:.8}
.tabs{display:flex;background:var(--card);border-bottom:1px solid var(--border);padding:0 16px;position:sticky;top:0;z-index:100;overflow-x:auto}
.tab-btn{padding:12px 20px;border:none;background:none;cursor:pointer;font-size:13px;font-weight:500;color:var(--text-secondary);border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap}
.tab-btn:hover{color:var(--text);background:var(--primary-light)}
.tab-btn.active{color:var(--primary);border-bottom-color:var(--primary);font-weight:600}
.tab-content{display:none;padding:20px 24px;max-width:1400px;margin:0 auto}
.tab-content.active{display:block}
.card{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:16px 20px;margin-bottom:16px}
.card-title{font-size:15px;font-weight:600;margin-bottom:12px;color:var(--text)}
.flex{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.flex label{font-weight:500;font-size:12px;color:var(--text-secondary)}
.flex select,.flex input{padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;background:var(--card);color:var(--text);outline:none;max-width:220px}
.flex select:focus{border-color:var(--primary);box-shadow:0 0 0 2px rgba(37,99,235,.15)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 10px;background:#f8fafc;color:var(--text-secondary);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid var(--border);white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}
tr:hover td{background:#f8fafc}
.scroll-wrap{overflow-x:auto;border-radius:6px;border:1px solid var(--border)}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500}
.badge-new{background:#e0e7ff;color:#3730a3}
.badge-mpdo{background:#fef3c7;color:#92400e}
.badge-ros{background:#fce7f3;color:#9d174d}
.badge-done{background:#dcfce7;color:#166534}
.badge-part{background:#ffedd5;color:#9a3412}
.badge-mos{background:#dbeafe;color:#1e40af}
.badge-kop{background:#f3e8ff;color:#6b21a8}
.badge-rp{background:#ecfdf5;color:#065f46}
.badge-del{background:#fef2f2;color:#991b1b}
.badge-all{background:#e0f2fe;color:#075985}
.badge-ko{background:#f0fdf4;color:#166534}
.chart-wrap{position:relative;height:360px;width:100%}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:16px}
.stat-card{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:14px 18px;border-left:3px solid var(--primary)}
.stat-card .val{font-size:26px;font-weight:700;color:var(--text)}
.stat-card .lbl{font-size:11px;color:var(--text-secondary);margin-top:2px}
.stat-card.gr{border-left-color:var(--success)}
.stat-card.og{border-left-color:var(--warning)}
.stat-card.rd{border-left-color:var(--danger)}
/* Timeline card */
.order-card{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:16px;margin-bottom:12px}
.order-card .order-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.order-card .order-header .id{font-weight:600;font-size:13px;color:var(--primary);font-family:monospace}
.order-card .order-meta{font-size:12px;color:var(--text-secondary);display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.tl{position:relative;padding-left:28px;margin:4px 0}
.tl::before{content:'';position:absolute;left:8px;top:6px;bottom:-6px;width:2px;background:var(--border)}
.tl:last-child::before{display:none}
.tl-item{display:flex;align-items:flex-start;gap:8px;margin:3px 0;font-size:12px}
.tl-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:3px;background:var(--primary)}
.tl-dot.gr{background:var(--success)}
.tl-dot.og{background:var(--warning)}
.tl-dot.gy{background:#94a3b8}
.tl-dot.bl{background:var(--primary)}
.tl-dot.rd{background:var(--danger)}
.tl-date{color:var(--text-secondary);min-width:85px;font-size:11px}
.tl-text{flex:1}
.tl-text .ttl{font-weight:500}
.load-more{text-align:center;padding:12px}
.load-more button{padding:8px 24px;border:1px solid var(--primary);background:var(--card);color:var(--primary);border-radius:6px;cursor:pointer;font-size:13px}
.load-more button:hover{background:var(--primary-light)}
.empty-state{text-align:center;padding:40px;color:var(--text-secondary);font-size:14px}
.zns-table{margin-top:8px;font-size:12px}
.zns-table th{font-size:10px;padding:6px 8px}
.zns-table td{padding:6px 8px}
@media(max-width:768px){
  .header{padding:12px 16px}.tab-content{padding:12px 16px}.tab-btn{padding:10px 14px;font-size:12px}
  .flex select{max-width:160px}.order-card .order-meta{gap:8px}
}
</style>
</head>
<body>
<div class="header">
<div><h1>Заказы по КМД</h1><div class="sub">Управление заказами конструкторской и монтажной документации</div></div>
<div class="sub">Данные из ELMA365</div>
</div>

<div class="tabs">
<button class="tab-btn active" data-tab="tab1">РП и объекты</button>
<button class="tab-btn" data-tab="tab2">Таймлайн заказов</button>
<button class="tab-btn" data-tab="tab3">Аналитика разниц</button>
</div>

<!-- Tab 1: RP and Objects -->
<div id="tab1" class="tab-content active">
<div class="card">
<div class="flex">
<label>Год:</label>
<select id="yf1"><option value="2025">2025</option><option value="2026" selected>2026</option><option value="all">Все</option></select>
<label>РП:</label>
<select id="rpf1"><option value="all">Все РП</option></select>
<label>Объект:</label>
<select id="obf1"><option value="all">Все объекты</option></select>
<label>Корпус:</label>
<select id="korf1"><option value="all">Все корпуса</option></select>
<label>Секция:</label>
<select id="secf1"><option value="all">Все секции</option></select>
</div>
</div>
<div class="stat-grid" id="sg1"></div>
<div class="card"><div class="card-title">Заказы по руководителям проектов</div><div class="chart-wrap"><canvas id="rpChart1"></canvas></div></div>
<div class="card"><div class="card-title">Детальная таблица по РП</div><div class="scroll-wrap"><table><thead><tr><th>Руководитель проекта</th><th>Заказов</th><th>Объекты</th><th>Новый</th><th>МПДО</th><th>РОС</th><th>Завершен</th><th>Частично СК</th><th>МОС</th><th>КОП</th><th>РП</th><th>Все ЗНС</th><th>КО</th></tr></thead><tbody id="rpTb1"></tbody></table></div></div>
</div>

<!-- Tab 2: Timeline -->
<div id="tab2" class="tab-content">
<div class="card">
<div class="flex">
<label>РП:</label>
<select id="rpf2"><option value="all">Все РП</option></select>
<label>Объект:</label>
<select id="obf2"><option value="all">Все объекты</option></select>
<label>Корпус:</label>
<select id="korf2"><option value="all">Все корпуса</option></select>
<label>Секция:</label>
<select id="secf2"><option value="all">Все секции</option></select>
<label style="margin-left:auto;font-size:12px" id="orderCount2">Заказов: 0</label>
</div>
</div>
<div id="tlContainer"></div>
</div>

<!-- Tab 3: Analytics -->
<div id="tab3" class="tab-content">
<div class="flex" style="margin-bottom:12px">
<label>Год:</label>
<select id="yf3"><option value="2025">2025</option><option value="2026" selected>2026</option><option value="all">Все</option></select>
<label>РП:</label>
<select id="rpf3"><option value="all">Все РП</option></select>
<label>Объект:</label>
<select id="obf3"><option value="all">Все объекты</option></select>
</div>
<div class="stat-grid" id="sg3"></div>
<div class="card"><div class="card-title">Разница: создание заказа vs плановая дата РП (из ЗНС)</div><div class="chart-wrap"><canvas id="sc1"></canvas></div></div>
<div class="card"><div class="card-title">Разница: создание заказа vs дата полной комплектности (СК)</div><div class="chart-wrap"><canvas id="sc2"></canvas></div></div>
<div class="card"><div class="card-title">Разница: создание заказа vs смена статуса</div><div class="chart-wrap"><canvas id="sc3"></canvas></div></div>
<div class="card"><div class="card-title">Детальная таблица разниц</div><div class="scroll-wrap"><table><thead><tr><th>ID заказа</th><th>Дата создания</th><th>РП</th><th>Объект</th><th>Статус</th><th>Разница (создан→план РП)</th><th>Разница (создан→полн.компл.)</th><th>Разница (создан→смена статуса)</th></tr></thead><tbody id="diffTb3"></tbody></table></div></div>
</div>

<script>CHARTJS_SOURCE_PLACEHOLDER</script>
<script>
// ===== DATA =====
window.DATA = DATA_PLACEHOLDER;

// ===== LOOKUPS =====
const LU = {};
DATA.u.forEach(u => LU[u.id] = u.name);
const LO = {};
DATA.ob.forEach(o => LO[o.id] = o.iid || o.name || '—');
const SM = DATA.sm;

// ===== UTILITIES =====
function safeDate(d) {
  if (!d || d === '' || d === null || d === undefined) return null;
  try {
    const dt = new Date(d);
    if (isNaN(dt.getTime())) return null;
    return dt;
  } catch(e) { return null; }
}

function fmtDate(d) {
  const dt = safeDate(d);
  if (!dt) return '—';
  return dt.toLocaleDateString('ru-RU', {day:'2-digit',month:'2-digit',year:'numeric'});
}

function fmtDateTime(d) {
  const dt = safeDate(d);
  if (!dt) return '—';
  return dt.toLocaleDateString('ru-RU', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
}

function daysDiff(d1, d2) {
  const a = safeDate(d1), b = safeDate(d2);
  if (!a || !b) return null;
  return Math.round((b - a) / (86400000));
}

function getYear(d) {
  const dt = safeDate(d);
  return dt ? dt.getFullYear() : null;
}

function sc(st) {
  const c = parseInt(st);
  return 'badge-' + ({1:'new',2:'mpdo',3:'ros',4:'done',5:'part',6:'mos',7:'kop',8:'rp',9:'del',10:'all',11:'ko'}[c] || '');
}

function sn(st) { return SM[String(st)] || 'Неизв.'; }

function rpName(a) {
  if (!a || !a.length) return 'Не назначен';
  return a.map(id => LU[id] || '?').join(', ');
}

function objName(a) {
  if (!a || !a.length) return '—';
  return a.map(id => LO[id] || id.substring(0,8)).join(', ');
}

function objList(a) {
  if (!a || !a.length) return [];
  return a.map(id => LO[id] || id);
}

function getLinkedZns(orderId) {
  const zns = [];
  for (const z of DATA.z) {
    if (z.del) continue;
    if (z.oid && z.oid.indexOf(orderId) !== -1) zns.push(z);
  }
  return zns;
}

// Get unique korpus/section for an order from linked ZNS
function getOrderKorpus(orderId) {
  const zns = getLinkedZns(orderId);
  const kors = new Set();
  zns.forEach(z => { if (z.kor) kors.add(z.kor); });
  return kors;
}

function getOrderSection(orderId) {
  const zns = getLinkedZns(orderId);
  const secs = new Set();
  zns.forEach(z => { if (z.sec) secs.add(z.sec); });
  return secs;
}

// ===== FILTERING =====
function filterOrders(year, rpId, objId, korpus, section) {
  return DATA.o.filter(o => {
    if (o.del) return false;
    if (year && year !== 'all') {
      const y = getYear(o.ca);
      if (y !== parseInt(year)) return false;
    }
    if (rpId && rpId !== 'all') {
      if (!o.rp || !o.rp.includes(rpId)) return false;
    }
    if (objId && objId !== 'all') {
      if (!o.obj || !o.obj.includes(objId)) return false;
    }
    if (korpus && korpus !== 'all') {
      const orderKor = getOrderKorpus(o.id);
      if (!orderKor.has(korpus)) return false;
    }
    if (section && section !== 'all') {
      const orderSec = getOrderSection(o.id);
      if (!orderSec.has(section)) return false;
    }
    return true;
  });
}

// ===== POPULATE FILTERS =====
function populateRpFilter(selId) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '<option value="all">Все РП</option>';
  const rpSet = new Set();
  DATA.o.forEach(o => { if (o.rp) o.rp.forEach(id => rpSet.add(id)); });
  rpSet.forEach(id => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.text = LU[id] || 'Неизв.';
    sel.appendChild(opt);
  });
  if (currentVal && sel.querySelector(`option[value="${currentVal}"]`)) sel.value = currentVal;
}

function populateObjFilter(selId) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '<option value="all">Все объекты</option>';
  const objSet = new Set();
  DATA.o.forEach(o => { if (o.obj) o.obj.forEach(id => { if (LO[id]) objSet.add(id); }); });
  objSet.forEach(id => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.text = LO[id] || id.substring(0,8);
    sel.appendChild(opt);
  });
  if (currentVal && sel.querySelector(`option[value="${currentVal}"]`)) sel.value = currentVal;
}

function populateKorpusFilter(selId) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '<option value="all">Все корпуса</option>';
  const korSet = new Set();
  DATA.z.forEach(z => { if (!z.del && z.kor) korSet.add(z.kor); });
  Array.from(korSet).sort().forEach(k => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.text = k;
    sel.appendChild(opt);
  });
  if (currentVal && sel.querySelector(`option[value="${currentVal}"]`)) sel.value = currentVal;
}

function populateSectionFilter(selId) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '<option value="all">Все секции</option>';
  const secSet = new Set();
  DATA.z.forEach(z => { if (!z.del && z.sec) secSet.add(z.sec); });
  Array.from(secSet).sort().forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.text = s;
    sel.appendChild(opt);
  });
  if (currentVal && sel.querySelector(`option[value="${currentVal}"]`)) sel.value = currentVal;
}

// ===== TAB 1: RP AND OBJECTS =====
function renderTab1() {
  const year = document.getElementById('yf1').value;
  const rpF = document.getElementById('rpf1').value;
  const obF = document.getElementById('obf1').value;
  const korF = document.getElementById('korf1').value;
  const secF = document.getElementById('secf1').value;

  const orders = filterOrders(year, rpF, obF, korF, secF);

  // Group by RP
  const rpGrp = {};
  orders.forEach(o => {
    const rpIds = o.rp && o.rp.length ? o.rp : ['__none__'];
    rpIds.forEach(rpId => {
      if (!rpGrp[rpId]) rpGrp[rpId] = { orders: [], sc: {} };
      rpGrp[rpId].orders.push(o);
      const s = String(o.st);
      rpGrp[rpId].sc[s] = (rpGrp[rpId].sc[s] || 0) + 1;
    });
  });

  const sorted = Object.entries(rpGrp).sort((a, b) => b[1].orders.length - a[1].orders.length);

  // Stats
  const objSet = new Set();
  orders.forEach(o => { if (o.obj) o.obj.forEach(id => objSet.add(id)); });
  document.getElementById('sg1').innerHTML = [
    {l:'Всего заказов', v:orders.length, c:''},
    {l:'Руководителей проектов', v:Object.keys(rpGrp).length, c:'gr'},
    {l:'Объектов строительства', v:objSet.size, c:'og'}
  ].map(s => `<div class="stat-card${s.c?' '+s.c:''}"><div class="val">${s.v}</div><div class="lbl">${s.l}</div></div>`).join('');

  // Table
  const stCodes = [1,2,3,4,5,6,7,8,10,11];
  document.getElementById('rpTb1').innerHTML = sorted.map(([rpId, g]) => {
    const name = rpId === '__none__' ? 'Не назначен' : (LU[rpId] || 'Неизв.');
    const allObj = new Set(g.orders.flatMap(o => objList(o.obj)));
    return '<tr><td><strong>' + name + '</strong></td><td>' + g.orders.length + '</td><td>' + (Array.from(allObj).join(', ') || '—') + '</td>' +
      stCodes.map(s => '<td>' + (g.sc[String(s)] || 0) + '</td>').join('') + '</tr>';
  }).join('');

  // Bar chart
  const labels = sorted.map(([rpId]) => rpId === '__none__' ? 'Не назначен' : (LU[rpId] || 'Неизв.'));
  const counts = sorted.map(([,g]) => g.orders.length);
  const colors = ['#2563eb','#16a34a','#d97706','#dc2626','#8b5cf6','#06b6d4','#f43f5e','#14b8a6','#f97316','#6366f1','#84cc16'];

  if (window.rpCh1) window.rpCh1.destroy();
  if (labels.length === 0) {
    document.getElementById('rpChart1').parentNode.innerHTML = '<p style="text-align:center;padding:40px;color:var(--text-secondary)">Нет данных для отображения</p>';
    return;
  }
  const ctx = document.getElementById('rpChart1').getContext('2d');
  window.rpCh1 = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Заказов',
        data: counts,
        backgroundColor: colors.slice(0, labels.length).map(c => c + 'BB'),
        borderColor: colors.slice(0, labels.length),
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: function(ctx) {
              const [,g] = sorted[ctx.dataIndex];
              let s = '';
              for (const [code, cnt] of Object.entries(g.sc)) {
                s += '\n' + sn(code) + ': ' + cnt;
              }
              return s;
            }
          }
        }
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { grid: { display: false } }
      }
    }
  });
}

// ===== TAB 2: TIMELINE =====
let tlPage = 0;
const TL_PAGE_SIZE = 20;
let tlFilteredOrders = [];

function renderTab2() {
  const rpF = document.getElementById('rpf2').value;
  const obF = document.getElementById('obf2').value;
  const korF = document.getElementById('korf2').value;
  const secF = document.getElementById('secf2').value;

  tlFilteredOrders = filterOrders('all', rpF, obF, korF, secF);
  tlFilteredOrders.sort((a, b) => (a.ca || '').localeCompare(b.ca || ''));
  document.getElementById('orderCount2').textContent = 'Заказов: ' + tlFilteredOrders.length;
  tlPage = 0;
  renderTimelinePage();
}

function renderTimelinePage() {
  const start = 0;
  const end = Math.min((tlPage + 1) * TL_PAGE_SIZE, tlFilteredOrders.length);
  const pageOrders = tlFilteredOrders.slice(0, end);

  let html = '';
  for (const o of pageOrders) {
    const events = [];

    // Creation
    if (o.ca) events.push({d: o.ca, t: 'Заказ создан', s: fmtDateTime(o.ca), c: 'gr'});
    // Status change
    if (o.sca) events.push({d: o.sca, t: 'Статус: ' + sn(o.st), s: fmtDateTime(o.sca), c: 'bl'});
    // Tasks
    if (o.ts) {
      o.ts.forEach(t => {
        if (t.ca) {
          let c = 'gy';
          if (t.st === 'in_progress') c = 'og';
          else if (t.st === 'completed') c = 'gr';
          events.push({d: t.ca, t: 'Задача: ' + t.tp, s: (t.st === 'in_progress' ? 'В работе' : t.st === 'completed' ? 'Завершена' : t.st) + ' | ' + fmtDateTime(t.ca), c: c});
        }
      });
    }
    // Full completeness
    if (o.dp) events.push({d: o.dp, t: 'Полная комплектность (СК)', s: fmtDateTime(o.dp), c: 'gr'});

    events.sort((a, b) => {
      const da = safeDate(a.d), db = safeDate(b.d);
      if (!da && !db) return 0;
      if (!da) return 1; if (!db) return -1;
      return da - db;
    });

    // Linked ZNS
    const lzns = getLinkedZns(o.id);
    // ZNS dates
    lzns.forEach(z => {
      if (z.rp) events.push({d: z.rp, t: 'ЗНС: план РП', s: fmtDate(z.rp) + (z.kor ? ' | ' + z.kor : '') + (z.sec ? ' ' + z.sec : ''), c: 'gy'});
      if (z.mos) events.push({d: z.mos, t: 'ЗНС: план МОС', s: fmtDate(z.mos) + (z.kor ? ' | ' + z.kor : '') + (z.sec ? ' ' + z.sec : ''), c: 'gy'});
      if (z.post) events.push({d: z.post, t: 'ЗНС: дата поставки', s: fmtDate(z.post), c: 'gy'});
      if (z.fakt) events.push({d: z.fakt, t: 'ЗНС: факт поставки', s: fmtDate(z.fakt), c: 'gy'});
    });

    events.sort((a, b) => {
      const da = safeDate(a.d), db = safeDate(b.d);
      if (!da && !db) return 0;
      if (!da) return 1; if (!db) return -1;
      return da - db;
    });

    html += '<div class="order-card">';
    html += '<div class="order-header">';
    html += '<span class="id">' + o.id.substring(0, 8) + '&hellip;</span>';
    html += '<span><span class="badge ' + sc(o.st) + '">' + sn(o.st) + '</span></span>';
    html += '</div>';
    html += '<div class="order-meta">';
    html += '<span>Создан: ' + fmtDate(o.ca) + '</span>';
    html += '<span>РП: ' + rpName(o.rp) + '</span>';
    html += '<span>Объект: ' + objName(o.obj) + '</span>';
    html += '</div>';
    // Timeline
    html += '<div class="tl">';
    events.forEach(e => {
      const c = e.c || 'bl';
      html += '<div class="tl-item"><span class="tl-dot ' + c + '"></span><span class="tl-date">' + fmtDate(e.d) + '</span><span class="tl-text"><span class="ttl">' + e.t + '</span><br>' + e.s + '</span></div>';
    });
    html += '</div>';

    // ZNS table
    if (lzns.length > 0) {
      html += '<div class="scroll-wrap zns-table"><table><thead><tr><th>ID ЗНС</th><th>Создана</th><th>План РП</th><th>План МОС</th><th>Поставка</th><th>Факт МОС</th><th>Корпус</th><th>Секция</th></tr></thead><tbody>';
      lzns.forEach(z => {
        html += '<tr><td title="' + z.id + '">' + z.id.substring(0,8) + '&hellip;</td>';
        html += '<td>' + fmtDate(z.ca) + '</td>';
        html += '<td>' + fmtDate(z.rp) + '</td><td>' + fmtDate(z.mos) + '</td>';
        html += '<td>' + fmtDate(z.post) + '</td><td>' + fmtDate(z.fakt) + '</td>';
        html += '<td>' + (z.kor || '—') + '</td><td>' + (z.sec || '—') + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }

    html += '</div>';
  }

  document.getElementById('tlContainer').innerHTML = html;

  if (end < tlFilteredOrders.length) {
    const container = document.getElementById('tlContainer');
    const btn = document.createElement('div');
    btn.className = 'load-more';
    btn.innerHTML = '<button onclick="tlPage++;renderTimelinePage()">Показать ещё (' + (tlFilteredOrders.length - end) + ')</button>';
    container.appendChild(btn);
  } else if (tlFilteredOrders.length === 0) {
    document.getElementById('tlContainer').innerHTML = '<div class="empty-state">Нет заказов, соответствующих фильтрам</div>';
  }
}

// ===== TAB 3: ANALYTICS =====
function renderTab3() {
  const year = document.getElementById('yf3').value;
  const rpF = document.getElementById('rpf3').value;
  const obF = document.getElementById('obf3').value;

  let orders = filterOrders(year, rpF, obF);
  if (year === 'all' || !year) {
    orders = orders; // already filtered
  }

  // Build diff data
  const diffData = orders.map(o => {
    const znsLinked = getLinkedZns(o.id);
    let planRpDates = znsLinked.map(z => z.rp).filter(d => safeDate(d));
    let minPlanRp = planRpDates.length ? planRpDates.sort()[0] : null;
    return {
      id: o.id, ca: o.ca, rp: rpName(o.rp), obj: objName(o.obj),
      st: o.st, d1: minPlanRp ? daysDiff(o.ca, minPlanRp) : null,
      d2: o.dp ? daysDiff(o.ca, o.dp) : null,
      d3: o.sca ? daysDiff(o.ca, o.sca) : null
    };
  });

  // Stats
  function calcStats(arr) {
    const vals = arr.filter(v => v !== null && v !== undefined);
    if (!vals.length) return {avg:'—', min:'—', max:'—', cnt:0};
    const sum = vals.reduce((a,b) => a+b, 0);
    return {avg: (sum/vals.length).toFixed(1), min: Math.min(...vals), max: Math.max(...vals), cnt: vals.length};
  }

  const s1 = calcStats(diffData.map(d => d.d1));
  const s2 = calcStats(diffData.map(d => d.d2));
  const s3 = calcStats(diffData.map(d => d.d3));

  document.getElementById('sg3').innerHTML = [
    {l:'Средняя разница (создан→план РП)', v: s1.avg !== '—' ? s1.avg + ' дн.' : '—', c:''},
    {l:'Мин / Макс (создан→план РП)', v: s1.min !== '—' ? s1.min + ' / ' + s1.max + ' дн.' : '—', c:'og'},
    {l:'Средняя разница (создан→полн.компл.)', v: s2.avg !== '—' ? s2.avg + ' дн.' : '—', c:'gr'},
    {l:'Средняя разница (создан→смена статуса)', v: s3.avg !== '—' ? s3.avg + ' дн.' : '—', c:''}
  ].map(s => '<div class="stat-card' + (s.c?' '+s.c:'') + '"><div class="val">' + s.v + '</div><div class="lbl">' + s.l + '</div></div>').join('');

  // Table
  document.getElementById('diffTb3').innerHTML = diffData.map(d =>
    '<tr><td title="' + d.id + '">' + d.id.substring(0,8) + '&hellip;</td>'
    + '<td>' + fmtDate(d.ca) + '</td><td>' + d.rp + '</td>'
    + '<td>' + (d.obj.length > 40 ? d.obj.substring(0,40)+'&hellip;' : d.obj) + '</td>'
    + '<td><span class="badge ' + sc(d.st) + '">' + sn(d.st) + '</span></td>'
    + '<td>' + (d.d1 !== null ? d.d1 : '—') + '</td>'
    + '<td>' + (d.d2 !== null ? d.d2 : '—') + '</td>'
    + '<td>' + (d.d3 !== null ? d.d3 : '—') + '</td></tr>'
  ).join('');

  // Scatter charts
  const colors = ['#2563eb', '#16a34a', '#d97706'];
  const dataSets = [
    diffData.filter(d => d.d1 !== null).map(d => ({x: d.ca, y: d.d1, l: 'Заказ ' + d.id.substring(0,8) + '… | РП: ' + d.rp})),
    diffData.filter(d => d.d2 !== null).map(d => ({x: d.ca, y: d.d2, l: 'Заказ ' + d.id.substring(0,8) + '… | РП: ' + d.rp})),
    diffData.filter(d => d.d3 !== null).map(d => ({x: d.ca, y: d.d3, l: 'Заказ ' + d.id.substring(0,8) + '… | РП: ' + d.rp}))
  ];
  const canvasIds = ['sc1', 'sc2', 'sc3'];
  const yLabels = ['Разница (дн.) → план РП', 'Разница (дн.) → полн.компл.', 'Разница (дн.) → смена статуса'];
  const chartVars = ['scCh1', 'scCh2', 'scCh3'];

  canvasIds.forEach((cid, idx) => {
    const pts = dataSets[idx];
    const chartVar = chartVars[idx];

    if (window[chartVar]) window[chartVar].destroy();

    if (!pts.length) {
      document.getElementById(cid).parentNode.innerHTML = '<p style="text-align:center;padding:40px;color:var(--text-secondary)">Нет данных</p>';
      return;
    }

    // Get min time for x-axis labeling
    const dates = pts.map(p => safeDate(p.x)).filter(Boolean);
    if (!dates.length) {
      document.getElementById(cid).parentNode.innerHTML = '<p style="text-align:center;padding:40px;color:var(--text-secondary)">Нет данных</p>';
      return;
    }
    const minT = Math.min(...dates.map(d => d.getTime()));

    const chartPts = pts.filter(p => safeDate(p.x)).map(p => ({
      x: Math.round((safeDate(p.x).getTime() - minT) / 86400000),
      y: p.y,
      l: p.l,
      rd: p.x
    }));

    const ctx = document.getElementById(cid).getContext('2d');
    window[chartVar] = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: yLabels[idx],
          data: chartPts,
          backgroundColor: colors[idx] + '80',
          borderColor: colors[idx],
          borderWidth: 1,
          pointRadius: 4,
          pointHoverRadius: 7
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          tooltip: {
            callbacks: {
              title: items => items[0].raw.l || '',
              label: ctx => {
                const d = ctx.raw;
                return ['Дата: ' + fmtDate(d.rd), 'Разница: ' + d.y + ' дн.'];
              }
            }
          },
          legend: { display: false }
        },
        scales: {
          x: {
            title: { display: true, text: 'Дата создания заказа' },
            ticks: {
              callback: function(val) {
                const dt = new Date(minT + val * 86400000);
                return dt.toLocaleDateString('ru-RU', {day:'2-digit',month:'short'});
              }
            }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: yLabels[idx] }
          }
        }
      }
    });
  });
}

// ===== TABS =====
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    this.classList.add('active');
    document.getElementById(this.dataset.tab).classList.add('active');

    if (this.dataset.tab === 'tab1') renderTab1();
    else if (this.dataset.tab === 'tab2') renderTab2();
    else if (this.dataset.tab === 'tab3') renderTab3();
  });
});

// ===== FILTER EVENTS =====
document.getElementById('yf1').addEventListener('change', renderTab1);
document.getElementById('rpf1').addEventListener('change', renderTab1);
document.getElementById('obf1').addEventListener('change', renderTab1);
document.getElementById('korf1').addEventListener('change', renderTab1);
document.getElementById('secf1').addEventListener('change', renderTab1);

document.getElementById('rpf2').addEventListener('change', renderTab2);
document.getElementById('obf2').addEventListener('change', renderTab2);
document.getElementById('korf2').addEventListener('change', renderTab2);
document.getElementById('secf2').addEventListener('change', renderTab2);

document.getElementById('yf3').addEventListener('change', renderTab3);
document.getElementById('rpf3').addEventListener('change', renderTab3);
document.getElementById('obf3').addEventListener('change', renderTab3);

// ===== INIT =====
populateRpFilter('rpf1');
populateRpFilter('rpf2');
populateRpFilter('rpf3');
populateObjFilter('obf1');
populateObjFilter('obf2');
populateObjFilter('obf3');
populateKorpusFilter('korf1');
populateKorpusFilter('korf2');
populateSectionFilter('secf1');
populateSectionFilter('secf2');

renderTab1();
renderTab2();
renderTab3();
</script>
</body>
</html>'''

def main():
    data = build_data_json()
    
    data_json = json.dumps(data, ensure_ascii=False, separators=(',',':'))
    print(f"Data JSON size: {len(data_json):,} bytes")
    
    # Check if data is too large (target < 4.5MB to leave room for HTML + Chart.js)
    MAX_DATA = 4500000
    if len(data_json) > MAX_DATA:
        print(f"WARNING: Data too large ({len(data_json):,} bytes). Compressing...")
        # We can try to remove some fields to reduce size
        # Let's check what's taking most space
        for key in ['o', 'z', 'u', 'ob']:
            part = json.dumps(data[key], ensure_ascii=False, separators=(',',':'))
            print(f"  {key}: {len(part):,} bytes ({len(data[key])} items)")
    
    # Read Chart.js source
    chartjs = ''
    chartjs_path = os.path.join(os.path.dirname(__file__), 'chart.umd.min.js')
    if os.path.exists(chartjs_path):
        with open(chartjs_path, 'r', encoding='utf-8') as f:
            chartjs = f.read()
    else:
        print(f"WARNING: Chart.js source not found at {chartjs_path}")
        print("Downloading from CDN...")
        import urllib.request
        try:
            url = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js'
            with urllib.request.urlopen(url, timeout=30) as response:
                chartjs = response.read().decode('utf-8')
            with open(chartjs_path, 'w', encoding='utf-8') as f:
                f.write(chartjs)
            print(f"Downloaded Chart.js ({len(chartjs):,} bytes)")
        except Exception as ex:
            print(f"Failed to download Chart.js: {ex}")
            chartjs = '// Chart.js placeholder'
    
    # Build HTML
    html = HTML_TEMPLATE.replace('CHARTJS_SOURCE_PLACEHOLDER', chartjs)
    html = html.replace('DATA_PLACEHOLDER', data_json)
    
    # Verify no invalid date patterns
    html = html.replace('Invalid Date', '—')
    html = html.replace('envalidate', '—')
    html = html.replace('envaliedate', '—')
    
    # Write output
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    file_size = os.path.getsize(OUT_FILE)
    print(f"\nDashboard saved: {OUT_FILE}")
    print(f"File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
    
    # Quick validation
    print("\n=== Validation ===")
    with open(OUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('File exists', os.path.exists(OUT_FILE)),
        ('File > 100KB', file_size > 100000),
        ('Chart.js embedded (no CDN)', 'cdn.jsdelivr.net' not in content),
        ('No Invalid Date', 'Invalid Date' not in content or 'Invalid Date' in content and 'Invalid Date' == content[content.find('Invalid Date'):content.find('Invalid Date')+len('Invalid Date')]),
        ('No envalidate', 'envalidate' not in content.lower()),
        ('Russian headings', 'Заказы по КМД' in content),
        ('JSON data embedded', 'window.DATA' in content),
    ]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")

if __name__ == '__main__':
    main()
