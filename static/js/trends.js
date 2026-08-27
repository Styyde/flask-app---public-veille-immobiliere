// static/js/trends.js
let typeDistributionChart = null;
let trendsMetaLoaded = false;

const TYPE_PIE_PALETTE = [
    '#2874a6', '#e67e22', '#8e44ad', '#27ae60', '#c0392b',
    '#16a085', '#d35400', '#7f8c8d',
];

function isoDate(d) {
    return d.toISOString().slice(0, 10);
}

function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return isoDate(d);
}

function formatVariation(pct) {
    if (pct === null || pct === undefined) {
        return '<span class="evo-trend evo-trend-neutre">—</span>';
    }
    if (pct > 0) return `<span class="evo-trend evo-trend-hausse">▲ +${pct}%</span>`;
    if (pct < 0) return `<span class="evo-trend evo-trend-baisse">▼ ${pct}%</span>`;
    return `<span class="evo-trend evo-trend-neutre">= 0%</span>`;
}

async function initEvolutionTab() {
    if (!trendsMetaLoaded) {
        await loadTrendsMeta();
        trendsMetaLoaded = true;

        const distFrom = document.getElementById('dist_date_from');
        const distTo = document.getElementById('dist_date_to');
        if (distFrom && !distFrom.value) distFrom.value = daysAgo(30);
        if (distTo && !distTo.value) distTo.value = daysAgo(0);

        const cvFrom = document.getElementById('cv_date_from');
        const cvTo = document.getElementById('cv_date_to');
        const cvCompareFrom = document.getElementById('cv_compare_from');
        const cvCompareTo = document.getElementById('cv_compare_to');
        if (cvFrom && !cvFrom.value) cvFrom.value = daysAgo(30);
        if (cvTo && !cvTo.value) cvTo.value = daysAgo(0);
        if (cvCompareFrom && !cvCompareFrom.value) cvCompareFrom.value = daysAgo(60);
        if (cvCompareTo && !cvCompareTo.value) cvCompareTo.value = daysAgo(31);

        const btnDist = document.getElementById('btn-dist-refresh');
        if (btnDist) btnDist.addEventListener('click', loadTypeDistribution);

        const btnCv = document.getElementById('btn-cv-compare');
        if (btnCv) btnCv.addEventListener('click', loadComparaisonVilles);
    }
    await Promise.all([loadTypeDistribution(), loadComparaisonVilles()]);
}

async function loadTrendsMeta() {
    try {
        const meta = await fetchJSON('/api/trends/meta');

        const villesContainer = document.getElementById('cv-villes-filter');
        if (villesContainer) {
            villesContainer.innerHTML = (meta.villes || []).map(v => `
                <label class="evo-type-chip">
                    <input type="checkbox" class="cv-ville-checkbox" value="${v}" checked>
                    ${v}
                </label>
            `).join('');
        }

        const typeSelect = document.getElementById('cv_type');
        if (typeSelect) {
            typeSelect.innerHTML = '<option value="">Tous</option>' +
                (meta.types || []).map(t => `<option value="${t}">${t}</option>`).join('');
        }
    } catch (err) {
        console.error('Erreur chargement meta tendances:', err);
    }
}

// ---- Répartition par type de bien ----

async function loadTypeDistribution() {
    const canvas = document.getElementById('chart-type-distribution');
    const emptyEl = document.getElementById('type-distribution-empty');
    if (!canvas) return;
    try {
        const params = new URLSearchParams();
        const from = document.getElementById('dist_date_from');
        const to = document.getElementById('dist_date_to');
        if (from && from.value) params.set('date_from', from.value);
        if (to && to.value) params.set('date_to', to.value);
        const data = await fetchJSON(`/api/trends/distribution-types?${params}`);
        renderTypeDistribution(data, emptyEl);
    } catch (err) {
        console.error('Erreur chargement répartition par type:', err);
    }
}

function renderTypeDistribution(data, emptyEl) {
    const canvas = document.getElementById('chart-type-distribution');
    if (!canvas) return;

    if (typeDistributionChart) { typeDistributionChart.destroy(); typeDistributionChart = null; }

    const distribution = (data && data.distribution) || [];
    if (distribution.length === 0) {
        if (emptyEl) emptyEl.classList.remove('hidden');
        canvas.style.visibility = 'hidden';
        return;
    }
    if (emptyEl) emptyEl.classList.add('hidden');
    canvas.style.visibility = 'visible';

    typeDistributionChart = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: distribution.map(d => d.type),
            datasets: [{
                data: distribution.map(d => d.pourcentage),
                backgroundColor: distribution.map((_, i) => TYPE_PIE_PALETTE[i % TYPE_PIE_PALETTE.length]),
                borderColor: '#fff',
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const item = distribution[ctx.dataIndex];
                            return ` ${item.type} : ${item.pourcentage}% (${item.nb_annonces} annonces)`;
                        },
                    },
                },
            },
        },
    });
}

// ---- Comparaison entre villes ----

function getSelectedVilles() {
    return Array.from(document.querySelectorAll('.cv-ville-checkbox'))
        .filter(b => b.checked)
        .map(b => b.value);
}

async function loadComparaisonVilles() {
    const tbody = document.querySelector('#table-comparaison-villes tbody');
    const emptyEl = document.getElementById('cv-empty');
    if (!tbody) return;

    const villes = getSelectedVilles();
    const dateFrom = document.getElementById('cv_date_from')?.value;
    const dateTo = document.getElementById('cv_date_to')?.value;

    if (villes.length === 0 || !dateFrom) {
        tbody.innerHTML = '';
        if (emptyEl) emptyEl.classList.remove('hidden');
        return;
    }

    try {
        const params = new URLSearchParams();
        params.set('villes', villes.join(','));
        const type = document.getElementById('cv_type')?.value;
        if (type) params.set('type', type);
        params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);
        const compareFrom = document.getElementById('cv_compare_from')?.value;
        const compareTo = document.getElementById('cv_compare_to')?.value;
        if (compareFrom) params.set('compare_from', compareFrom);
        if (compareTo) params.set('compare_to', compareTo);

        const data = await fetchJSON(`/api/trends/comparaison-villes?${params}`);
        const rows = data.villes || [];

        if (rows.length === 0) {
            tbody.innerHTML = '';
            if (emptyEl) emptyEl.classList.remove('hidden');
            return;
        }
        if (emptyEl) emptyEl.classList.add('hidden');

        tbody.innerHTML = rows.map(r => `
            <tr>
                <td>${r.ville}</td>
                <td>${formatPrixM2(r.mediane)}</td>
                <td>${formatVariation(r.variation_pct)}</td>
                <td>${r.stock}</td>
                <td>${formatVariation(r.variation_stock_pct)}</td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Erreur chargement comparaison villes:', err);
    }
}
