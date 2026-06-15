const messagesEl = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const agentList = document.getElementById('agentList');
const dataStatus = document.getElementById('dataStatus');

userInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    userInput.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = '...';
    try {
        const res = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text })
        });
        const data = await res.json();
        addMessage(data.answer || 'Нет ответа', 'bot');
    } catch (e) {
        addMessage('Ошибка соединения с сервером', 'bot');
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Отправить';
    }
}

function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = 'message ' + sender;
    div.innerHTML = '<div class="msg-content">' + escapeHtml(text) + '</div>';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(t) {
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
}

async function loadAgents() {
    try {
        const res = await fetch('/api/agents');
        const data = await res.json();
        agentList.innerHTML = data.agents.map(a =>
            '<div class="agent-item">' + a.name + '</div>'
        ).join('');
    } catch (e) {
        agentList.innerHTML = '<div style="color:#6c6c8a;font-size:12px">ошибка</div>';
    }
}

async function loadDataStatus() {
    try {
        const res = await fetch('/api/data-status');
        const data = await res.json();
        dataStatus.innerHTML = 'Сущностей: ' + data.entities_count + '<br>Обновлено: ' + (data.oldest_hours ? Math.round(data.oldest_hours) + 'ч назад' : 'нет данных');
    } catch (e) {
        dataStatus.innerHTML = 'ошибка';
    }
}

async function refreshData() {
    dataStatus.innerHTML = 'обновляю...';
    try {
        const res = await fetch('/api/refresh', { method: 'POST' });
        const data = await res.json();
        dataStatus.innerHTML = 'обновлено: ' + data.updated;
    } catch (e) {
        dataStatus.innerHTML = 'ошибка обновления';
    }
}

loadAgents();
loadDataStatus();
