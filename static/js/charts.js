// static/js/charts.js
let histogramChart = null;
let comparisonChart = null;
let scatterChart = null;
let lastScatterData = null;
let scatterToggleBound = false;

const CHART_COLORS = {
    primary: '#2874a6',
    primaryLight: 'rgba(40, 116, 166, 0.6)',
    success: 'rgba(46, 204, 113, 0.7)',
    grid: '#e8edf2',
};

const SOURCE_COLORS = {
    'Al Omrane': { bg: 'rgba(40, 116, 166, 0.65)', border: '#2874a6' },
    'Sarouty': { bg: 'rgba(230, 126, 34, 0.65)', border: '#e67e22' },
    'Mubawab': { bg: 'rgba(142, 68, 173, 0.65)', border: '#8e44ad' },
};

const OPP_COLOR = { bg: 'rgba(39, 174, 96, 0.85)', border: '#1e8449' };

function renderCharts(data) {
    renderHistogram(data.histogram);
    renderComparison(data.comparaison);
    renderScatter(data.scatter || []);
    renderOpportunities(data.opportunites);
}

function getScatterYMode() {
    const checked = document.querySelector('input[name="scatter-y"]:checked');
    return checked ? checked.value : 'prix';
}

function bindScatterToggle() {
    if (scatterToggleBound) return;
    document.querySelectorAll('input[name="scatter-y"]').forEach(radio => {
        radio.addEventListener('change', () => {
            if (lastScatterData) renderScatter(lastScatterData);
        });
    });
    scatterToggleBound = true;
}

function linearRegression(points) {
    const n = points.length;
    if (n < 2) return null;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    for (const p of points) {
        sumX += p.x;
        sumY += p.y;
        sumXY += p.x * p.y;
        sumXX += p.x * p.x;
    }
    const denom = n * sumXX - sumX * sumX;
    if (denom === 0) return null;
    const a = (n * sumXY - sumX * sumY) / denom;
    const b = (sumY - a * sumX) / n;
    return { a, b };
}

function formatAxisPrice(val) {
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + ' M';
    if (val >= 1_000) return (val / 1_000).toFixed(0) + ' K';
    return Math.round(val).toLocaleString('fr-FR');
}

function buildScatterDatasets(points, yMode) {
    const sources = ['Al Omrane', 'Sarouty', 'Mubawab'];
    const datasets = [];

    sources.forEach(source => {
        const colors = SOURCE_COLORS[source] || SOURCE_COLORS['Al Omrane'];
        const normal = points.filter(p => p.source === source && !p.est_opportunite);
        const opps = points.filter(p => p.source === source && p.est_opportunite);

        if (normal.length) {
            datasets.push({
                label: source,
                data: normal.map(p => ({
                    x: p.surface,
                    y: yMode === 'prix_m2' ? p.prix_m2 : p.prix,
                    _meta: p,
                })),
                backgroundColor: colors.bg,
                borderColor: colors.border,
                pointRadius: 5,
                pointHoverRadius: 7,
            });
        }

        if (opps.length) {
            datasets.push({
                label: `${source} (opportunité)`,
                data: opps.map(p => ({
                    x: p.surface,
                    y: yMode === 'prix_m2' ? p.prix_m2 : p.prix,
                    _meta: p,
                })),
                backgroundColor: OPP_COLOR.bg,
                borderColor: OPP_COLOR.border,
                pointRadius: 8,
                pointHoverRadius: 10,
                borderWidth: 2,
            });
        }
    });

    if (yMode === 'prix_m2' && points.length >= 2) {
        const regPoints = points.map(p => ({ x: p.surface, y: p.prix_m2 }));
        const reg = linearRegression(regPoints);
        if (reg) {
            const xs = points.map(p => p.surface);
            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            datasets.push({
                label: 'Tendance prix/m²',
                type: 'line',
                data: [
                    { x: minX, y: reg.a * minX + reg.b },
                    { x: maxX, y: reg.a * maxX + reg.b },
                ],
                borderColor: 'rgba(231, 76, 60, 0.7)',
                borderWidth: 2,
                borderDash: [6, 4],
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                order: 0,
            });
        }
    }

    return datasets;
}

function renderScatter(points) {
    bindScatterToggle();

    const canvas = document.getElementById('chart-scatter');
    const emptyEl = document.getElementById('scatter-empty');
    if (!canvas) return;

    lastScatterData = points || [];

    if (scatterChart) {
        scatterChart.destroy();
        scatterChart = null;
    }

    if (!points || points.length === 0) {
        if (emptyEl) emptyEl.classList.remove('hidden');
        canvas.style.visibility = 'hidden';
        return;
    }

    if (emptyEl) emptyEl.classList.add('hidden');
    canvas.style.visibility = 'visible';

    const yMode = getScatterYMode();
    const yLabel = yMode === 'prix_m2' ? 'Prix/m² (DH)' : 'Prix total (DH)';
    const datasets = buildScatterDatasets(points, yMode);

    scatterChart = new Chart(canvas, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick(_event, elements) {
                if (!elements.length) return;
                const el = elements[0];
                const meta = scatterChart.data.datasets[el.datasetIndex].data[el.index];
                if (meta && meta._meta && meta._meta.url) {
                    openUrl(meta._meta.url);
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { boxWidth: 10, font: { size: 11 } },
                },
                tooltip: {
                    callbacks: {
                        title(items) {
                            const meta = items[0]?.raw?._meta;
                            return meta ? fmt(meta.titre) : '';
                        },
                        label(ctx) {
                            const p = ctx.raw._meta;
                            if (!p) return '';
                            const lines = [
                                `Source : ${fmt(p.source)}`,
                                `Localisation : ${fmt(p.localisation)}`,
                                `Surface : ${formatSurface(p.surface)}`,
                                `Prix : ${formatPrix(p.prix)}`,
                                `Prix/m² : ${formatPrixM2(p.prix_m2)}`,
                            ];
                            if (p.est_opportunite && p.ecart_pourcent != null) {
                                lines.push(`Écart : ${p.ecart_pourcent}% vs moyenne`);
                            }
                            if (p.url) lines.push('Cliquer pour ouvrir');
                            return lines;
                        },
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Surface (m²)' },
                    grid: { color: CHART_COLORS.grid },
                },
                y: {
                    title: { display: true, text: yLabel },
                    grid: { color: CHART_COLORS.grid },
                    ticks: {
                        callback: val => formatAxisPrice(val),
                    },
                },
            },
        },
    });
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

    if (!opportunites || opportunites.length === 0) {
        container.innerHTML = `
            <div style="padding: 25px 15px; text-align: center; color: #7f8c8d; background: #f8f9fa; border-radius: 8px; border: 1px dashed #bdc3c7;">
                <p style="margin: 0; font-weight: 600; font-size: 1.05em; color: #2c3e50;">Aucun bien ne correspond à ces filtres.</p>
                <p style="margin: 6px 0 0 0; font-size: 0.9em;">Essayez d'élargir vos critères de recherche (ville, type, budget, source).</p>
            </div>`;
        return;
    }

    const hasRealOpportunities = opportunites.some(o => o.est_opportunite);
    let html = '';

    if (!hasRealOpportunities) {
        html += `
            <div style="margin-bottom: 15px; padding: 12px 15px; background-color: #fff3cd; color: #856404; border-radius: 6px; font-size: 0.9em; border-left: 4px solid #ffeeba;">
                <strong>Aucune opportunité forte détectée (seuil > 15%).</strong><br>
                Voici les biens affichant les meilleurs prix/m² pour le sous-ensemble sélectionné :
            </div>
        `;
    }

    html += opportunites.map(o => `
        <div class="opp-card ${o.est_opportunite ? 'hot' : ''}"
             ${o.url ? `style="cursor:pointer" data-url="${escapeAttr(o.url)}"` : ''}>
            <div>
                <div class="opp-title">${fmt(o.titre)}</div>
                <div class="opp-meta">
                    ${fmt(o.localisation)} · ${fmt(o.type_bien)}
                    ${o.est_opportunite ? ' <span class="opp-badge" style="background:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-size:0.8em; margin-left:5px; font-weight:bold;">🔥 Forte valeur</span>' : ''}
                </div>
                <div class="opp-meta">
                    ${o.source ? `<span style="color:#34495e; font-weight:600;">[${fmt(o.source)}]</span> ` : ''}
                    ${o.lot_titre || o.lot ? `Lot ${fmt(o.lot_titre || o.lot)} ` : ''}
                    ${o.no_produit ? `— Produit ${fmt(o.no_produit)}` : ''}
                </div>
            </div>
            <div class="opp-price" style="text-align:right;">
                <strong style="display:block; font-size: 1.1em; color: #2c3e50;">${formatPrixM2(o.prix_m2)}</strong>
                <span style="font-size: 0.85em; font-weight: 500; color: ${o.ecart_pourcent < 0 ? '#27ae60' : '#e74c3c'};">
                    ${o.ecart_pourcent != null ? (o.ecart_pourcent > 0 ? '+' : '') + o.ecart_pourcent + '% vs moyenne' : ''}
                </span>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;

    container.querySelectorAll('[data-url]').forEach(el => {
        el.addEventListener('click', () => {
            if (typeof openUrl === 'function') {
                openUrl(el.dataset.url);
            } else {
                window.open(el.dataset.url, '_blank');
            }
        });
    });
}

function escapeAttr(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}
