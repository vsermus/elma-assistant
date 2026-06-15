import json

files = [
    'data/raboty_po_tenderu.json',
    'data/tender.json',
    'data/spravochnik_id.json',
    'data/_companies.json',
    'data/users.json'
]

for file in files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle different JSON structures (some have 'result' -> 'result')
            result = data
            if isinstance(data, dict) and 'result' in data:
                result = data['result']
                if isinstance(result, dict) and 'result' in result:
                    result = result['result']

            if isinstance(result, list) and len(result) > 0:
                print(f"File: {file}")
                print(f"Keys: {result[0].keys()}")
                print("-" * 20)
            else:
                print(f"File: {file} - No data found in expected format.")
    except Exception as e:
        print(f"Error reading {file}: {e}")
