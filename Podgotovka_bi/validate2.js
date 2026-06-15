const fs = require('fs');
const html = fs.readFileSync('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/dashboards/загрузка_тэо_гант.html', 'utf8');
const start = html.indexOf('<script>');
const end = html.indexOf('</script>', start);
const script = html.slice(start + 8, end);

const lines = script.split('\n');
let depth = 0;
let minDepth = 0;
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  for (const ch of line) {
    if (ch === '{') depth++;
    if (ch === '}') depth--;
  }
  if (depth < minDepth) {
    minDepth = depth;
    console.log('Depth goes negative at line ' + (i+1) + ': depth=' + depth);
  }
}
console.log('Final depth: ' + depth);
console.log('Min depth: ' + minDepth);
