const fs = require('fs');
const html = fs.readFileSync('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/dashboards/загрузка_тэо_гант.html', 'utf8');
const start = html.indexOf('<script>');
const end = html.indexOf('</script>', start);
const script = html.slice(start + 8, end);

const lines = script.split('\n');
// Count function declarations
let funcCount = 0;
for (const line of lines) {
  if (line.trim().startsWith('function ') && line.includes('(')) funcCount++;
}
console.log('Functions found: ' + funcCount);
console.log('Total lines: ' + lines.length);
