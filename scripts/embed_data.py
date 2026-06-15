"""Встраивает JSON-данные в HTML-дашборд (для работы при file:// открытии)."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def embed(data_rel_path, html_rel_path):
    data_file = os.path.join(ROOT, data_rel_path)
    html_file = os.path.join(ROOT, html_rel_path)

    # читаем JSON
    with open(data_file, 'r', encoding='utf-8') as f:
        raw_json = f.read()

    # читаем HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    # Текст для замены: блок функции loadData
    old_block = """  // ── Load data ──
  function loadData() {
    fetch('../data/ozm.json')
      .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function(json) {
        allData = (json.result && json.result.result) || json.result || [];
        buildDashboard();
      })
      .catch(function(err) {
        document.body.innerHTML = '<div style="padding:60px;text-align:center;color:#f85149;">' +
          '<h2>Ошибка загрузки данных</h2><p style="margin-top:8px;color:#8b8e97;">' + err.message + '</p>' +
          '<p style="margin-top:4px;color:#6b6e77;">Убедитесь, что файл data/ozm.json доступен.</p></div>';
      });
  }"""

    # Экранируем </script> и </ для безопасной вставки в <script>
    safe_json = raw_json.replace('</script>', '<\\/script>').replace('</', '<\\/')

    new_block = f"""  // ── Embedded data (file:// safe) ──
  const EMBEDDED_DATA = {safe_json};

  function loadData() {{
    allData = (EMBEDDED_DATA.result && EMBEDDED_DATA.result.result) || EMBEDDED_DATA.result || [];
    buildDashboard();
  }}"""

    if old_block not in html:
        print("ОШИБКА: не найден блок loadData в HTML", file=sys.stderr)
        sys.exit(1)

    html = html.replace(old_block, new_block, 1)

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(html_file) / 1024
    data = json.loads(raw_json)
    records = len(data.get('result', {}).get('result', []))
    print(f"Готово: {os.path.basename(html_rel_path)} ({size_kb:.0f} KB, {records} записей, данные встроены)")

if __name__ == '__main__':
    embed('data/ozm.json', 'dashboards/ozm_report.html')
