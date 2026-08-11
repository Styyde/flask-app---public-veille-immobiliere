// static/js/trends.js
let evoPrixChart = null;
let evoNbChart = null;
let evoMetaLoaded = false;

const EVO_COLOR_PALETTE = [
    '#2874a6', '#e67e22', '#8e44ad', '#27ae60', '#c0392b',
    '#16a085', '#d35400', '#2c3e50', '#f39c12', '#7f8c8d',
];

function evoColorForIndex(i) {
    return EVO_COLOR_PALETTE[i % EVO_COLOR_PALETTE.length];
}

async function initEvolutionTab() {
    if (!evoMetaLoaded) {
        await loadEvolutionMeta();
        evoMetaLoaded = true;
        const btn = document.getElementById('btn-evo-refresh');
        if (btn) btn.addEventListener('click', loadEvolutionCharts);
    }
    await loadEvolutionCharts();
}

async function loadEvolutionMeta() {
    try {
        const meta = await fetchJSON('/api/trends/meta');
        const container = document.getElementById('evo-types-filter');
        if (!container) return;
        container.innerHTML = (meta.types || []).map(t => `
            <label class="evo-type-chip">
                <input type="checkbox" class="evo-type-checkbox" value="${t}" checked>
                ${t}
            </label>
        `).join('');
        container.querySelectorAll('.evo-type-checkbox').forEach(cb => {
            cb.addEventListener('change', loadEvolutionCharts);
        });
    } catch (err) {
        console.error('Erreur chargement meta évolution:', err);
    }
}

function getSelectedEvoTypes() {
    const boxes = document.querySelectorAll('.evo-type-checkbox');
    const all = Array.from(boxes);
    const checked = all.filter(b => b.checked).map(b => b.value);
    if (checked.length === 0 || checked.length === all.length) return null; // pas de filtre = tous
    return checked;
}

function buildEvoParams(metric) {
    const params = new URLSearchParams();
    params.set('metric', metric);
    const granularite = document.getElementById('evo_granularite');
    if (granularite && granularite.value) params.set('granularite', granularite.value);
    const dateFrom = document.getElementById('evo_date_from');
    if (dateFrom && dateFrom.value) params.set('date_from', dateFrom.value);
    const dateTo = document.getElementById('evo_date_to');
    if (dateTo && dateTo.value) params.set('date_to', dateTo.value);
    const types = getSelectedEvoTypes();
    if (types) params.set('types', types.join(','));
    return params;
}

async function loadEvolutionCharts() {
    try {
        const [prixData, nbData] = await Promise.all([
            fetchJSON(`/api/trends/evolution?${buildEvoParams('prix_m2')}`),
            fetchJSON(`/api/trends/evolution?${buildEvoParams('nb_annonces')}`),
        ]);
        renderEvolutionChart('chart-evolution-prix', 'evo-prix-empty', 'prix', prixData, 'Prix/m² (DH)');
        renderEvolutionChart('chart-evolution-nb', 'evo-nb-empty', 'nb', nbData, "Nombre d'annonces");
    } catch (err) {
        console.error('Erreur chargement évolution:', err);
    }
}

function renderEvolutionChart(canvasId, emptyElId, which, data, yLabel) {
    const canvas = document.getElementById(canvasId);
    const emptyEl = document.getElementById(emptyElId);
    if (!canvas) return;

    const hasData = data && data.series && data.series.length > 0 && data.periodes.length > 0;

    if (which === 'prix' && evoPrixChart) { evoPrixChart.destroy(); evoPrixChart = null; }
    if (which === 'nb' && evoNbChart) { evoNbChart.destroy(); evoNbChart = null; }

    if (!hasData) {
        if (emptyEl) emptyEl.classList.remove('hidden');
        canvas.style.visibility = 'hidden';
        return;
    }
    if (emptyEl) emptyEl.classList.add('hidden');
    canvas.style.visibility = 'visible';

    const datasets = data.series.map((s, i) => {
        const color = evoColorForIndex(i);
        return {
            label: s.serie,
            data: s.points.map(p => p.valeur),
            borderColor: color,
            backgroundColor: color,
            spanGaps: true,
            tension: 0.25,
            pointRadius: 4,
            pointHoverRadius: 6,
        };
    });

    const chart = new Chart(canvas, {
        type: 'line',
        data: { labels: data.periodes, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
            },
            scales: {
                x: { grid: { color: CHART_COLORS.grid } },
                y: { beginAtZero: false, title: { display: true, text: yLabel }, grid: { color: CHART_COLORS.grid } },
            },
        },
    });

    if (which === 'prix') evoPrixChart = chart;
    else evoNbChart = chart;
}
