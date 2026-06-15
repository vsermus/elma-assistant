const fs = require('fs');
const html = fs.readFileSync('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/dashboards/загрузка_тэо_гант.html', 'utf8');
const start = html.indexOf('<script>');
const end = html.indexOf('</script>', start);
const script = html.slice(start + 8, end);

const opens = (script.match(/\{/g) || []).length;
const closes = (script.match(/\}/g) || []).length;
console.log('Braces: open=' + opens + ' close=' + closes + (opens === closes ? ' OK' : ' MISMATCH'));

// Check for duplicate function names
const funcs = script.match(/function (\w+)/g);
if (funcs) {
  const counts = {};
  funcs.forEach(f => { counts[f] = (counts[f] || 0) + 1; });
  for (const [f, c] of Object.entries(counts)) {
    if (c > 1) console.log('DUPLICATE: ' + f + ' (' + c + 'x)');
  }
}
console.log('Functions found: ' + funcs.length);
