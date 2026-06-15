import sys, json, os
sys.path.insert(0, r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector')

# Load the module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    'server_mod', 
    r'C:\Users\админ\Desktop\Проекты Claude\ELMA_Connector\subprojects\dashboard-builder\server\server.py'
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

config = {
    'entities': ['raboty_po_tenderu'],
    'metrics': [{'entity': 'raboty_po_tenderu', 'field': 'kvadratura'}],
    'dimensions': [{'entity': 'raboty_po_tenderu', 'field': '__status'}],
    'chart_type': 'bar',
    'aggregation': 'sum',
    'metric_labels': {'kvadratura': 'Площадь, м²'},
    'group_labels': {'__status': 'Статус'},
    'filters': [],
}
try:
    result = mod.build_dashboard(config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)[:2000])
except Exception as e:
    import traceback
    traceback.print_exc()
