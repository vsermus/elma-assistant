import json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_template.html")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_grafik")


def unwrap(data):
    if isinstance(data, dict):
        for key in ("result", "items", "data", "statusItems"):
            if key in data:
                inner = data[key]
                if isinstance(inner, (list, dict)):
                    if isinstance(inner, dict) and "result" in inner:
                        return inner["result"]
                    return inner
    return data


def load_and_clean(name):
    path = os.path.join(DATA_DIR, name)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    items = unwrap(raw)
    if isinstance(items, list):
        items = [r for r in items if isinstance(r, dict) and not r.get("__deletedAt")]
    return items


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def main():
    print("Loading data...")
    vitrage = load_and_clean("kartochka_vitrazha_po_km.json")
    sprav = load_and_clean("spravochnik_id.json")
    zadanie = load_and_clean("zadanie_na_kmd.json")
    users = load_and_clean("users.json")

    status_path = os.path.join(DATA_DIR, "statusy_zadanie_na_kmd.json")
    statuses = {}
    if os.path.exists(status_path):
        with open(status_path, encoding="utf-8") as f:
            raw = json.load(f)
        raw = unwrap(raw)
        if isinstance(raw, list):
            for s in raw:
                if isinstance(s, dict) and "id" in s:
                    statuses[s["id"]] = s

    print(f"  vitrage: {len(vitrage)}")
    print(f"  sprav: {len(sprav)}")
    print(f"  zadanie: {len(zadanie)}")
    print(f"  users: {len(users)}")
    print(f"  statuses: {len(statuses)}")

    # Clean and recreate
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    data_out = os.path.join(OUTPUT_DIR, "data")
    os.makedirs(data_out)

    write_json(os.path.join(data_out, "vitrage.json"), vitrage)
    write_json(os.path.join(data_out, "sprav.json"), sprav)
    write_json(os.path.join(data_out, "zadanie.json"), zadanie)
    write_json(os.path.join(data_out, "users.json"), users)
    write_json(os.path.join(data_out, "statusy.json"), statuses)

    # Copy template
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # Write start script
    ps1 = '''$port = 8000
Write-Host ""
Write-Host "========================================"
Write-Host "  Demo: http://localhost:$port"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""
python -m http.server $port --bind 127.0.0.1
'''
    with open(os.path.join(OUTPUT_DIR, "start_demo.ps1"), "w", encoding="utf-8") as f:
        f.write(ps1)

    # Size report
    sizes = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fn in files:
            fp = os.path.join(root, fn)
            sz = os.path.getsize(fp)
            rel = os.path.relpath(fp, OUTPUT_DIR)
            sizes.append((rel, sz))
            print(f"  {rel}: {sz/1024:.0f} KB")
    total_kb = sum(s for _, s in sizes) / 1024
    print(f"\nTotal: {total_kb:.0f} KB")
    print(f"Folder: {OUTPUT_DIR}")
    print("Run: cd demo_grafik && .\start_demo.ps1")


if __name__ == "__main__":
    main()
