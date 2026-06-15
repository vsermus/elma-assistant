const fs = require('fs');
const html = fs.readFileSync('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/dashboards/загрузка_тэо_гант.html', 'utf8');
const start = html.indexOf('<script>');
const end = html.indexOf('</script>', start);
const script = html.slice(start + 8, end);

// Try parsing as module
try {
  // Check for basic syntax by looking at function declarations balance
  const opens = (script.match(/\{/g) || []).length;
  const closes = (script.match(/\}/g) || []).length;
  console.log('Braces: open=' + opens + ' close=' + closes + (opens === closes ? ' OK' : ' MISMATCH'));

  const openParens = (script.match(/\(/g) || []).length;
  const closeParens = (script.match(/\)/g) || []).length;
  console.log('Parens: open=' + openParens + ' close=' + closeParens + (openParens === closeParens ? ' OK' : ' MISMATCH'));

} catch(e) {
  console.log('Error:', e.message);
}
