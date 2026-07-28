// static/js/charts.js
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

    // 1. Cas sans aucune donnée pour ces filtres
    if (!opportunites || opportunites.length === 0) {
        container.innerHTML = `
            <div style="padding: 25px 15px; text-align: center; color: #7f8c8d; background: #f8f9fa; border-radius: 8px; border: 1px dashed #bdc3c7;">
                <p style="margin: 0; font-weight: 600; font-size: 1.05em; color: #2c3e50;">Aucun bien ne correspond à ces filtres.</p>
                <p style="margin: 6px 0 0 0; font-size: 0.9em;">Essayez d'élargir vos critères de recherche (ville, type, budget, source).</p>
            </div>`;
        return;
    }

    // 2. Vérification de la présence d'opportunités à forte valeur
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

    // 3. Construction des cartes
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