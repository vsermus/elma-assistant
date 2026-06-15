const fs = require('fs');
const html = fs.readFileSync('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/dashboards/загрузка_тэо_гант.html', 'utf8');
const start = html.indexOf('<script>');
const end = html.indexOf('</script>', start);
const script = html.slice(start + 8, end);
const lines = script.split('\n');
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('function init')) {
    console.log('init at line ' + (i+1) + ': ' + lines[i]);
  }
}
