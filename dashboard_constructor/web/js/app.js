const API_BASE = 'http://localhost:8000/api';

class DataStore {
    constructor() {
        this.data = {};
        this.translations = { system: {}, entities: {} };
        this.relationships = {
            'raboty_po_tenderu': { 'tender': 'tender' },
            'tender': { 'id_proekta_1': 'spravochnik_id' },
            'spravochnik_id': { 'zakazchik': '_companies' },
            'statusy_rabot_po_tenderam': { 'id': 'statusy_rabot_po_tenderam' }
        };
    }

    async loadTranslations() {
        const res = await fetch(`${API_BASE}/translations`);
        this.translations = await res.json();
    }

    async loadEntity(entityId) {
        const res = await fetch(`${API_BASE}/data/${entityId}`);
        this.data[entityId] = await res.json();
    }

    getTranslation(entityId, field) {
        if (this.translations.system[field]) return this.translations.system[field];
        if (this.translations.entities[entityId] && this.translations.entities[entityId][field]) {
            return this.translations.entities[entityId][field];
        }
        // Better fallback: replace underscores and lowercase
        return field.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
    }

    resolveReference(entityId, record, field) {
        const refId = record[field];
        if (!refId) return '—';
        const targetEntity = this.relationships[entityId]?.[field];
        if (!targetEntity) return refId;
        const targetData = this.data[targetEntity];
        if (!targetData) return refId;
        const match = targetData.find(item => item.__id === refId);
        if (match) {
            return match.name || match.fio || match.itogovyi_id || refId;
        }
        return refId;
    }
}

const store = new DataStore();
let selectedMetrics = [];

async function init() {
    try {
        await store.loadTranslations();
        const res = await fetch(`${API_BASE}/entities`);
        const entities = await res.json();

        const container = document.getElementById('entity-selection');
        entities.forEach(entity => {
            const group = document.createElement('div');
            group.className = 'entity-group';

            const name = document.createElement('label');
            name.className = 'entity-name';
            name.innerHTML = `<input type="checkbox" value="${entity.id}"> ${entity.name || entity.id}`;

            const metricsDiv = document.createElement('div');
            metricsDiv.style.display = 'none';
            metricsDiv.className = 'metrics-list';
            metricsDiv.dataset.entity = entity.id;

            name.querySelector('input').onchange = async (e) => {
                if (e.target.checked) {
                    metricsDiv.style.display = 'block';
                    await store.loadEntity(entity.id);
                    renderMetrics(entity.id, metricsDiv);
                } else {
                    metricsDiv.style.display = 'none';
                    selectedMetrics = selectedMetrics.filter(m => m.entity !== entity.id);
                    renderDashboard();
                }
            };

            group.appendChild(name);
            group.appendChild(metricsDiv);
            container.appendChild(group);
        });
    } catch (e) {
        console.error("Init error:", e);
        alert("Ошибка при загрузке настроек. Проверьте, запущен ли сервер.");
    }
}

function renderMetrics(entityId, container) {
    const data = store.data[entityId];
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #ccc; font-size: 0.8rem;">Нет данных</div>';
        return;
    }

    const fields = Object.keys(data[0]);
    container.innerHTML = '';

    const metricsCol = document.createElement('div');
    metricsCol.className = 'metrics-column';
    metricsCol.innerHTML = '<div class="column-title">Показатели (Числа)</div>';

    const attrCol = document.createElement('div');
    attrCol.className = 'metrics-column';
    attrCol.innerHTML = '<div class="column-title">Атрибуты (Текст)</div>';

    const wrapper = document.createElement('div');
    wrapper.className = 'metrics-container';
    wrapper.appendChild(metricsCol);
    wrapper.appendChild(attrCol);

    fields.forEach(field => {
        const label = store.getTranslation(entityId, field);
        const item = document.createElement('label');
        item.className = 'metric-item';
        item.innerHTML = `<input type="checkbox" value="${field}"> ${label}`;

        item.querySelector('input').onchange = (e) => {
            if (e.target.checked) {
                selectedMetrics.push({ entity: entityId, field });
            } else {
                selectedMetrics = selectedMetrics.filter(m => !(m.entity === entityId && m.field === field));
            }
            renderDashboard();
        };

        const sampleValue = data[0][field];
        if (typeof sampleValue === 'number') {
            metricsCol.appendChild(item);
        } else {
            attrCol.appendChild(item);
        }
    });

    container.appendChild(wrapper);
}

async function renderDashboard() {
    const grid = document.getElementById('dashboard-grid');
    if (selectedMetrics.length === 0) {
        grid.innerHTML = '<div class="empty-state">Выберите сущности и метрики в боковом меню, чтобы начать построение отчета</div>';
        return;
    }

    grid.innerHTML = '';

    selectedMetrics.forEach(metric => {
        const card = document.createElement('div');
        card.className = 'chart-card';

        const title = document.createElement('h3');
        title.innerText = store.getTranslation(metric.entity, metric.field);
        card.appendChild(title);

        const canvas = document.createElement('canvas');
        card.appendChild(canvas);
        grid.appendChild(card);

        createChart(canvas, metric);
    });
}

function createChart(canvas, metric) {
    const data = store.data[metric.entity] || [];
    if (data.length === 0) return;

    const values = data.map(item => item[metric.field]);
    const isNumeric = typeof values.find(v => v !== null && v !== undefined) === 'number';

    if (isNumeric) {
        const sorted = [...data].sort((a, b) => b[metric.field] - a[metric.field]).slice(0, 10);
        const labels = sorted.map((item, i) => `Запись ${i+1}`);
        const numericValues = sorted.map(item => item[metric.field]);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: store.getTranslation(metric.entity, metric.field),
                    data: numericValues,
                    backgroundColor: '#3498db'
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    } else {
        // Categorical: Bar chart instead of Pie
        const counts = {};
        values.forEach(v => {
            const val = v === null || v === undefined ? 'Пусто' : v;
            counts[val] = (counts[val] || 0) + 1;
        });

        const labels = Object.keys(counts);
        const numericValues = Object.values(counts);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Количество',
                    data: numericValues,
                    backgroundColor: '#2ecc71'
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y', // Horizontal bar for better readability of long names
                scales: { x: { beginAtZero: true } }
            }
        });
    }
}

document.getElementById('btn-update').onclick = async () => {
    const btn = document.getElementById('btn-update');
    const status = document.getElementById('update-status');
    btn.disabled = true;
    status.innerText = 'Обновление...';
    try {
        const res = await fetch(`${API_BASE}/update`, { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            status.innerText = 'Данные обновлены!';
            for (let entityId in store.data) {
                await store.loadEntity(entityId);
            }
            renderDashboard();
        } else {
            alert('Ошибка обновления: ' + result.error);
            status.innerText = 'Ошибка обновления';
        }
    } catch (e) {
        alert('Ошибка сервера: ' + e.message);
        status.innerText = 'Ошибка сервера';
    } finally {
        btn.disabled = false;
        setTimeout(() => { status.innerText = 'Готов'; }, 3000);
    }
};

init();
