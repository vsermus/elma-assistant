const fs = require('fs');
const html = fs.readFileSync('C:/Users/админ/Desktop/Проекты Claude/ELMA_Connector/dashboards/загрузка_тэо_гант.html', 'utf8');
const start = html.indexOf('<script>');
const end = html.indexOf('</script>', start);
const script = html.slice(start + 8, end);

const opens = (script.match(/\{/g) || []).length;
const closes = (script.match(/\}/g) || []).length;
console.log('Braces: ' + opens + '/' + closes + (opens === closes ? ' OK' : ' MISMATCH'));

const fopens = (script.match(/\(/g) || []).length;
const fcloses = (script.match(/\)/g) || []).length;
console.log('Parens: ' + fopens + '/' + fcloses + (fopens === fcloses ? ' OK' : ' MISMATCH'));

// Check for duplicate function names
const funcRegex = /\bfunction\s+(\w+)\s*\(/g;
let match;
const funcCounts = {};
while ((match = funcRegex.exec(script)) !== null) {
  funcCounts[match[1]] = (funcCounts[match[1]] || 0) + 1;
}
let hasDuplicates = false;
for (const [name, count] of Object.entries(funcCounts)) {
  if (count > 1) {
    console.log('DUPLICATE: ' + name + ' (' + count + 'x)');
    hasDuplicates = true;
  }
}
if (!hasDuplicates) console.log('No duplicate functions');
console.log('Total unique functions: ' + Object.keys(funcCounts).length);
