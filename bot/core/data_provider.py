import json
import os
import datetime


class DataProvider:
    def __init__(self, config):
        base = os.path.normpath(os.path.join(
            os.path.dirname(__file__), '..', config['data']['base_path']
        ))
        self.base_path = base
        self.entities_config_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), '..', config['data']['entities_config']
        ))
        self.cache = {}

    def get_entity_list(self):
        with open(self.entities_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_entity(self, entity_id):
        if entity_id in self.cache:
            return self.cache[entity_id]
        path = os.path.join(self.base_path, f'{entity_id}.json')
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('result', {}).get('result', data.get('items', []))
        self.cache[entity_id] = items
        return items

    def get_all_loaded_entity_ids(self):
        entities = []
        for fname in os.listdir(self.base_path):
            if fname.endswith('.json'):
                entities.append(fname.replace('.json', ''))
        return sorted(entities)

    def get_data_age_hours(self, entity_id):
        path = os.path.join(self.base_path, f'{entity_id}.json')
        if not os.path.exists(path):
            return None
        mtime = os.path.getmtime(path)
        age = datetime.datetime.now() - datetime.datetime.fromtimestamp(mtime)
        return age.total_seconds() / 3600

    def clear_cache(self):
        self.cache = {}

    def refresh_entity(self, entity_id):
        self.cache.pop(entity_id, None)
        return self.load_entity(entity_id)
