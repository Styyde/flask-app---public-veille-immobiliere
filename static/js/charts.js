let histogramChart = null;
let comparisonChart = null;

const CHART_COLORS = {
    primary: '#2874a6',
    primaryLight: 'rgba(40, 116, 166, 0.6)',
    success: 'rgba(46, 204, 113, 0.7)',
    grid: '#e8edf2',
};

function renderCharts(data) {
    renderHistogram(data.histogram);
    renderComparison(data.comparaison);
    renderOpportunities(data.opportunites);
}

function renderHistogram(hist) {
    const canvas = document.getElementById('chart-histogram');
    if (!canvas || !hist) return;

    if (histogramChart) histogramChart.destroy();

    histogramChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: hist.labels || [],
            datasets: [{
                label: 'Nombre de biens',
                data: hist.counts || [],
                backgroundColor: CHART_COLORS.primaryLight,
                borderColor: CHART_COLORS.primary,
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: CHART_COLORS.grid } },
                x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } },
            },
        },
    });
}

function renderComparison(comparaison) {
    const canvas = document.getElementById('chart-comparison');
    if (!canvas || !comparaison) return;

    if (comparisonChart) comparisonChart.destroy();

    const labels = comparaison.map(c => c.groupe || 'Inconnu').slice(0, 12);
    const values = comparaison.map(c => c.prix_m2_moyen).slice(0, 12);

    comparisonChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Prix/m² moyen (DH)',
                data: values,
                backgroundColor: CHART_COLORS.success,
                borderColor: '#27ae60',
                borderWidth: 1,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, grid: { color: CHART_COLORS.grid } },
                y: { grid: { display: false } },
            },
        },
    });
}

function renderOpportunities(opportunites) {
    const container = document.getElementById('opportunities-list');
    if (!container) return;

    if (!opportunites || !opportunites.length) {
        container.innerHTML = '<p style="color:#7f8c8d">Aucune opportunité détectée pour le moment.</p>';
        return;
    }

    container.innerHTML = opportunites.map(o => `
        <div class="opp-card ${o.est_opportunite ? 'hot' : ''}"
             ${o.url ? `style="cursor:pointer" data-url="${o.url}"` : ''}>
            <div>
                <div class="opp-title">${fmt(o.titre)}</div>
                <div class="opp-meta">
                    ${fmt(o.localisation)} · ${fmt(o.type_bien)}
                    ${o.est_opportunite ? ' <span class="opp-badge">Forte valeur</span>' : ''}
                </div>
                <div class="opp-meta">Lot ${fmt(o.lot_titre)} — Produit ${fmt(o.no_produit)}</div>
            </div>
            <div class="opp-price">
                ${formatPrixM2(o.prix_m2)}
                <div class="opp-meta">${o.ecart_pourcent != null ? o.ecart_pourcent + '% vs moyenne' : ''}</div>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('[data-url]').forEach(el => {
        el.addEventListener('click', () => openUrl(el.dataset.url));
    });
}