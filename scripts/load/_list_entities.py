import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config, json

entities = json.load(open(config.ENTITIES_CONFIG, encoding='utf-8'))
for e in entities:
    print(f'  {e["id"]:30s} - {e["name"]}')
