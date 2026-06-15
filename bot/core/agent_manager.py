import os
import json


class AgentManager:
    def __init__(self, data_provider, config):
        self.data = data_provider
        self.agents_config = config.get('agents', {})
        self.rules_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), '..', 'rules'
        ))

    def get_agent_for_query(self, query):
        query_lower = query.lower()
        kmd_keywords = ['кмд', 'задание', 'витраж', 'озм', 'заказ материал', 'знс', 'снабжение',
                        'kartochka', 'zadanie', 'order_by_kmd', 'zns', 'чертеж', 'карточка']
        tender_keywords = ['тендер', 'работа', 'raboty', 'tender', 'подряд', 'договор',
                          'заказчик', 'объект', 'строительств']
        excel_keywords = ['excel', 'xlsx', 'график', 'выгрузка', 'отчёт', 'отчет', 'скачать',
                         'эксель', 'таблица', 'диаграмма', 'экспорт']
        directory_keywords = ['компани', 'сотрудник', 'пользовател', 'справочник',
                             'users', 'companies', 'статус', 'контрагент']

        scores = {
            'kmd': sum(1 for kw in kmd_keywords if kw in query_lower),
            'tender': sum(1 for kw in tender_keywords if kw in query_lower),
            'excel': sum(1 for kw in excel_keywords if kw in query_lower),
            'directory': sum(1 for kw in directory_keywords if kw in query_lower),
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'general'

    def get_agent_rules(self, agent_id):
        path = os.path.join(self.rules_path, f'{agent_id}_rules.md')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ''

    def get_agent_info(self, agent_id):
        info = self.agents_config.get(agent_id, {})
        return {
            'id': agent_id,
            'name': info.get('name', agent_id),
            'enabled': info.get('enabled', False),
            'entities': info.get('entities', [])
        }

    def list_agents(self):
        return [self.get_agent_info(aid) for aid in self.agents_config]

    def process_query(self, query):
        agent_id = self.get_agent_for_query(query)
        agent_info = self.get_agent_info(agent_id)
        rules = self.get_agent_rules(agent_id)
        entity_data = {}
        for eid in agent_info.get('entities', []):
            data = self.data.load_entity(eid)
            if data:
                entity_data[eid] = data[:5]

        return {
            'agent': agent_info,
            'matched_keywords': agent_id,
            'rules': rules,
            'sample_data': entity_data,
            'original_query': query
        }
