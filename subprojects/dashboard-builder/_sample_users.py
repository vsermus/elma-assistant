import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import scripts.config as cfg

with open(os.path.join(cfg.DATA_DIR, 'users.json'), encoding='utf-8') as f:
    data = json.load(f)
recs = data['result']['result']
with open(os.path.join(os.path.dirname(__file__), '_sample.txt'), 'w', encoding='utf-8') as out:
    for i, r in enumerate(recs[:5]):
        out.write(f'Запись {i+1}:\n')
        out.write(f'  __name: {r["__name"]}\n')
        fn = r['fullname']
        out.write(f'  fullname: last="{fn["lastname"]}", first="{fn["firstname"]}", mid="{fn["middlename"]}"\n\n')
