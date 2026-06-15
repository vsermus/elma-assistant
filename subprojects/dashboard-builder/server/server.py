import json, os, sys, http.server, urllib.parse, subprocess, copy, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
import scripts.config as cfg

DATA_DIR = ROOT / 'data'
SUBPROJECT_DIR = ROOT / 'subprojects' / 'dashboard-builder'
FRONTEND_DIR = SUBPROJECT_DIR / 'frontend'
CONFIG_DIR = SUBPROJECT_DIR / 'config'
PORT = 8008

TOKEN = None
ENV_PATH = ROOT / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('ELMA_TOKEN='):
            TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

# Load metadata
with open(CONFIG_DIR / 'field_metadata.json', encoding='utf-8') as f:
    ENTITY_META = {e['id']: e for e in json.load(f)}

# --- Data loading ---
DATA_CACHE = {}
FIELD_TYPES = {}  # entity_id -> {field: type}

def load_entity_data(eid):
    if eid in DATA_CACHE:
        return DATA_CACHE[eid]
    path = DATA_DIR / f'{eid}.json'
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    records = None
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        if 'result' in data and isinstance(data['result'], dict) and 'result' in data['result']:
            records = data['result']['result']
        elif 'result' in data and isinstance(data['result'], list):
            records = data['result']
        elif 'statusItems' in data:
            records = data['statusItems']
        elif 'items' in data:
            records = data['items']
    records = records or []
    DATA_CACHE[eid] = records
    return records

def get_field_type(eid, field):
    if eid not in FIELD_TYPES:
        FIELD_TYPES[eid] = {}
        meta = ENTITY_META.get(eid)
        if meta:
            for f in meta.get('fields', []):
                FIELD_TYPES[eid][f['key']] = f
    fmeta = FIELD_TYPES[eid].get(field, {})
    return fmeta.get('type'), fmeta.get('linkTo')

def format_user(fullname):
    if not fullname or not isinstance(fullname, dict):
        return str(fullname) if fullname else ''
    parts = [fullname.get('lastname', '')]
    if fullname.get('firstname'):
        initials = fullname['firstname'][0] + '.'
        if fullname.get('middlename'):
            initials += fullname['middlename'][0] + '.'
        parts.append(initials)
    return ' '.join(parts)

def resolve_link(eid, field, value):
    ftype, link_to = get_field_type(eid, field)
    if not link_to or not value:
        return value
    # value might be a list of IDs or a single ID
    ids = value if isinstance(value, list) else [value]
    linked_records = load_entity_data(link_to)
    lookup = {}
    for r in linked_records:
        rid = r.get('__id', r.get('id'))
        if link_to == 'users':
            lookup[rid] = format_user(r.get('fullname', {}))
        elif link_to in ('_companies',):
            lookup[rid] = r.get('__name', r.get('name', rid))
        else:
            lookup[rid] = r.get('__name', r.get('name', rid))
    resolved = [lookup.get(v, str(v)) for v in ids]
    return ', '.join(resolved) if resolved else str(value)

def extract_money(val):
    if isinstance(val, dict) and 'cents' in val:
        return round(val['cents'] / 100, 2)
    if isinstance(val, (int, float)):
        return val
    return None

def extract_value(val):
    if isinstance(val, dict) and 'cents' in val:
        return round(val['cents'] / 100, 2)
    if val is None:
        return None
    if isinstance(val, list):
        return ', '.join(str(v) for v in val)
    return val

def format_display(eid, field, val):
    # Handle __status: {"order": 0, "status": 3} -> lookup in statusy_rabot_po_tenderam
    if field == '__status' and isinstance(val, dict):
        status_id = val.get('status')
        if status_id is not None:
            status_records = load_entity_data('statusy_rabot_po_tenderam')
            for sr in status_records:
                if sr.get('id') == status_id:
                    return sr.get('name', str(status_id))
            return str(status_id)
        return str(val)
    ftype, link_to = get_field_type(eid, field)
    if ftype == 'link' and link_to:
        return resolve_link(eid, field, val)
    if ftype == 'metric' and isinstance(val, dict) and 'cents' in val:
        return extract_money(val)
    if isinstance(val, dict):
        if '__name' in val:
            return val.get('__name', '')
        if 'name' in val:
            return val.get('name', '')
    if isinstance(val, list) and len(val) == 1 and isinstance(val[0], dict) and '__name' in val[0]:
        return val[0]['__name']
    return val

def build_dashboard(config):
    entity_ids = config.get('entities', [])
    metrics = config.get('metrics', [])
    dimensions = config.get('dimensions', [])
    filters = config.get('filters', [])
    chart_type = config.get('chart_type', 'table')
    aggregation = config.get('aggregation', 'sum')
    group_labels = config.get('group_labels', {})
    metric_labels = config.get('metric_labels', {})

    if not entity_ids:
        return {'error': 'No entities selected'}

    # Load primary entity data
    primary_eid = entity_ids[0]
    records = load_entity_data(primary_eid)
    if not records:
        return {'error': f'No data for {primary_eid}'}

    # Apply filters
    for f in filters:
        feid = f.get('entity', primary_eid)
        ffield = f['field']
        fop = f.get('op', 'eq')
        fval = f['value']
        filtered = []
        for r in records:
            cell = r.get(ffield)
            cell_str = str(cell).lower() if cell else ''
            fval_str = str(fval).lower()
            if fop == 'eq' and cell_str == fval_str:
                filtered.append(r)
            elif fop == 'contains' and fval_str in cell_str:
                filtered.append(r)
            elif fop == 'gte':
                cv = extract_money(cell) if cell else 0
                if cv is not None and cv >= float(fval):
                    filtered.append(r)
            elif fop == 'lte':
                cv = extract_money(cell) if cell else 0
                if cv is not None and cv <= float(fval):
                    filtered.append(r)
            elif fop == 'date_gte':
                if cell and cell >= str(fval):
                    filtered.append(r)
            elif fop == 'date_lte':
                if cell and cell <= str(fval):
                    filtered.append(r)
        records = filtered

    # Group and aggregate
    groups = {}
    for r in records:
        key_parts = []
        for d in dimensions:
            val = format_display(d.get('entity', primary_eid), d['field'], r.get(d['field']))
            if val is None:
                val = '(пусто)'
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            key_parts.append(str(val))
        key = '|'.join(key_parts)

        if key not in groups:
            groups[key] = {tuple(d['field'] for d in dimensions): key_parts}
            for m in metrics:
                groups[key][m['field']] = 0

        for m in metrics:
            val = r.get(m['field'])
            numeric = extract_money(val)
            if numeric is not None:
                groups[key][m['field']] += numeric

    # Convert to chart format
    if not groups:
        return {'labels': [], 'datasets': [], 'chart_type': chart_type}

    sorted_keys = sorted(groups.keys(), key=lambda k: groups[k][tuple(d['field'] for d in dimensions)][0] if dimensions else k)

    labels = []
    for k in sorted_keys:
        parts = groups[k][tuple(d['field'] for d in dimensions)]
        labels.append(' | '.join(parts) if len(parts) > 1 else parts[0])

    datasets = []
    for m in metrics:
        data_vals = [groups[k][m['field']] for k in sorted_keys]
        label = metric_labels.get(m['field'], m['field'])
        datasets.append({'label': label, 'data': data_vals})

    # For table mode, also include per-record data
    table_data = None
    if chart_type == 'table':
        table_data = []
        for r in records[:500]:
            row = {}
            for d in dimensions:
                deid = d.get('entity', primary_eid)
                val = format_display(deid, d['field'], r.get(d['field']))
                dlabel = group_labels.get(d['field'], d['field'])
                row[dlabel] = str(val) if val is not None else ''
            for m in metrics:
                val = format_display(primary_eid, m['field'], r.get(m['field']))
                mlabel = metric_labels.get(m['field'], m['field'])
                row[mlabel] = val if val is not None else 0
            table_data.append(row)

    return {
        'labels': labels,
        'datasets': datasets,
        'chart_type': chart_type,
        'table_data': table_data,
        'total_records': len(records),
    }


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/entities':
            self.send_json(self.get_entities_info())
        elif path == '/api/health':
            self.send_json({'status': 'ok'})
        elif path.startswith('/api/data/'):
            eid = path.split('/api/data/')[1].split('?')[0]
            self.send_json({'data': load_entity_data(eid), 'total': len(load_entity_data(eid))})
        else:
            # Try serving static files
            if path == '/' or path == '':
                path = '/index.html'
            filepath = FRONTEND_DIR / path.lstrip('/')
            if filepath.exists() and filepath.is_file():
                ext = filepath.suffix.lower()
                mime_map = {
                    '.html': 'text/html; charset=utf-8',
                    '.js': 'application/javascript; charset=utf-8',
                    '.css': 'text/css; charset=utf-8',
                    '.json': 'application/json; charset=utf-8',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.svg': 'image/svg+xml',
                }
                mime = mime_map.get(ext, 'application/octet-stream')
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len else b'{}'
        data = json.loads(body) if body else {}

        if path == '/api/build':
            try:
                result = build_dashboard(data)
                self.send_json(result)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f'BUILD ERROR: {e}\n{tb}')
                self.send_json({'error': str(e), 'traceback': tb}, 500)
        elif path == '/api/entities':
            self.send_json(self.get_entities_info())
        elif path == '/api/refresh':
            result = self.refresh_data(data)
            self.send_json(result)
        else:
            self.send_json({'error': 'Not found'}, 404)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def get_entities_info(self):
        info = []
        for eid, meta in ENTITY_META.items():
            fields = []
            for f in meta.get('fields', []):
                if f['type'] == 'skip':
                    continue
                fields.append({
                    'key': f['key'],
                    'name': f['name'],
                    'type': f['type'],
                    'linkTo': f.get('linkTo'),
                })
            info.append({
                'id': eid,
                'name': meta['name'],
                'description': meta.get('description', ''),
                'fields': fields,
            })
        return info

    def refresh_data(self, data):
        entity_ids = data.get('entities', [])
        try:
            args = ['python', 'scripts/load/load_data.py'] + entity_ids
            result = subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT), timeout=180)
            # Clear cache
            for eid in entity_ids or list(DATA_CACHE.keys()):
                DATA_CACHE.pop(eid, None)
            if entity_ids:
                for eid in entity_ids:
                    load_entity_data(eid)
            return {'success': True, 'output': result.stdout + result.stderr}
        except Exception as e:
            return {'success': False, 'error': str(e)}


def main():
    server = http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler)
    print(f'Dashboard Builder запущен: http://localhost:{PORT}')
    print(f'Горячие клавиши: Ctrl+C для остановки')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nОстановка...')
        server.shutdown()


if __name__ == '__main__':
    main()
