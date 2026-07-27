let activeTab = 'alomrane';

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initFilters();
    loadStats();
    document.getElementById('btn-search').addEventListener('click', search);
    document.getElementById('btn-reset').addEventListener('click', resetFilters);
    document.getElementById('btn-scrape-ao').addEventListener('click', scrapeAlomrane);
    document.getElementById('btn-scrape-sar').addEventListener('click', scrapeSarouty);
    document.getElementById('btn-scrape-mub').addEventListener('click', scrapeMubawab);
    document.getElementById('source').addEventListener('change', onSourceChange);
    setTimeout(search, 300);
});

function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            activeTab = tab.dataset.tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`tab-${activeTab}`).classList.add('active');
        });
    });
}

function initFilters() {
    onSourceChange();
}

function onSourceChange() {
    const source = document.getElementById('source').value;
    updateOptions(source);
    if (source === 'sarouty') setActiveTab('sarouty');
    else if (source === 'alomrane') setActiveTab('alomrane');
    else if (source === 'mubawab') setActiveTab('mubawab');
}

function setActiveTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach(c => {
        c.classList.toggle('active', c.id === `tab-${tab}`);
    });
}

async function loadStats() {
    try {
        const data = await fetchJSON('/api/stats');
        renderStats(data);
        populateRegions(data.regions || []);
        updateOptions('all');
    } catch (err) {
        document.getElementById('stats-cards').innerHTML =
            `<div class="stat-card">Erreur stats : ${err.message}</div>`;
    }
}

function renderStats(data) {
    const cards = [
        { label: 'Projets Al Omrane', value: data.nb_projets || 0 },
        { label: 'Lots', value: data.nb_lots || 0 },
        { label: 'Produits', value: data.nb_produits || 0 },
        { label: 'Annonces Sarouty', value: data.nb_sarouty || 0 },
        { label: 'Annonces Mubawab', value: data.nb_mubawab || 0 },
    ];
    document.getElementById('stats-cards').innerHTML = cards.map(c => `
        <div class="stat-card">
            <div class="value">${Number(c.value).toLocaleString('fr-FR')}</div>
            <div class="label">${c.label}</div>
        </div>
    `).join('');
}

function populateRegions(regions) {
    const sel = document.getElementById('region_select');
    const existing = new Set([...sel.options].map(o => o.value));
    regions.forEach(r => {
        if (existing.has(String(r.id))) return;
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = r.nom;
        sel.appendChild(opt);
    });
}

async function updateOptions(source) {
    try {
        const data = await fetchJSON(`/api/options?source=${source}`);
        const datalist = document.getElementById('villes-list');
        datalist.innerHTML = '';
        (data.villes || []).forEach(v => {
            const opt = document.createElement('option');
            opt.value = v;
            datalist.appendChild(opt);
        });
        const typeSelect = document.getElementById('type_bien');
        const current = typeSelect.value;
        typeSelect.innerHTML = '<option value="">Type</option>';
        (data.types || []).forEach(t => {
            const opt = document.createElement('option');
            opt.value = t;
            opt.textContent = t;
            typeSelect.appendChild(opt);
        });
        if (current) typeSelect.value = current;
    } catch (err) {
        console.error('Options error:', err);
    }
}

async function search() {
    const params = buildFilterParams();
    const source = document.getElementById('source').value;

    document.getElementById('alomrane-list').innerHTML =
        '<div class="yt-loading">Chargement…</div>';
    document.getElementById('tbody-sarouty').innerHTML =
        '<tr><td colspan="7" class="empty">Chargement…</td></tr>';
    document.getElementById('tbody-mubawab').innerHTML =
        '<tr><td colspan="7" class="empty">Chargement…</td></tr>';

    const promises = [];
    const loadAo = source === 'all' || source === 'alomrane';
    const loadSar = source === 'all' || source === 'sarouty';
    const loadMub = source === 'all' || source === 'mubawab';

    if (loadAo) {
        const p = new URLSearchParams(params);
        p.delete('source');
        promises.push(
            fetchJSON(`/api/alomrane/projets?${p}`).then(renderAlomrane).catch(e => {
                document.getElementById('alomrane-list').innerHTML =
                    `<div class="yt-error">${e.message}</div>`;
            })
        );
    } else {
        document.getElementById('alomrane-list').innerHTML =
            '<div class="empty-state">Autre source sélectionnée</div>';
        document.getElementById('count-ao').textContent = '0';
    }

    if (loadSar) {
        const p = new URLSearchParams(params);
        p.delete('source');
        promises.push(
            fetchJSON(`/api/sarouty/annonces?${p}`).then(renderSarouty).catch(e => {
                document.getElementById('tbody-sarouty').innerHTML =
                    `<tr><td colspan="7" class="empty" style="color:red">${e.message}</td></tr>`;
            })
        );
    } else {
        document.getElementById('tbody-sarouty').innerHTML =
            '<tr><td colspan="7" class="empty">Autre source sélectionnée</td></tr>';
        document.getElementById('count-sar').textContent = '0';
    }

    if (loadMub) {
        const p = new URLSearchParams(params);
        p.delete('source');
        promises.push(
            fetchJSON(`/api/mubawab/annonces?${p}`).then(renderMubawab).catch(e => {
                document.getElementById('tbody-mubawab').innerHTML =
                    `<tr><td colspan="7" class="empty" style="color:red">${e.message}</td></tr>`;
            })
        );
    } else {
        document.getElementById('tbody-mubawab').innerHTML =
            '<tr><td colspan="7" class="empty">Autre source sélectionnée</td></tr>';
        document.getElementById('count-mub').textContent = '0';
    }

    promises.push(
        fetchJSON(`/api/analytics?${params}`).then(renderCharts).catch(console.error)
    );

    await Promise.all(promises);
}

function resetFilters() {
    ['budget_min', 'budget_max', 'ville', 'type_bien',
     'surface_min', 'surface_max', 'prix_m2_min', 'prix_m2_max'].forEach(id => {
        document.getElementById(id).value = '';
    });
    document.getElementById('source').value = 'all';
    onSourceChange();
    search();
}

function showStatus(msg, type = 'info') {
    const el = document.getElementById('scraping-status');
    el.className = `scraping-status ${type}`;
    el.textContent = msg;
    el.classList.remove('hidden');
}

async function scrapeAlomrane() {
    const regionId = document.getElementById('region_select').value;
    const btn = document.getElementById('btn-scrape-ao');
    if (!regionId) { alert('Veuillez sélectionner une région.'); return; }

    btn.disabled = true;
    showStatus('Scraping Al Omrane en cours…', 'info');

    try {
        const data = await fetch('/api/scraper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region_ids: [parseInt(regionId)], deep: false }),
        }).then(r => r.json());

        if (data.error) throw new Error(data.error);
        showStatus(`✅ ${data.nouveaux_projets} nouveaux projets trouvés.`, 'success');
        await loadStats();
        await search();
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
    }
}

async function scrapeSarouty() {
    const btn = document.getElementById('btn-scrape-sar');
    btn.disabled = true;
    showStatus('Scraping Sarouty en cours… (max 5 pages)', 'info');

    try {
        const data = await fetch('/api/scraper_sarouty', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                max_pages: 5,
                region: document.getElementById('region_sarouty').value,
                category: document.getElementById('category_sarouty').value,
            }),
        }).then(r => r.json());

        if (data.error) throw new Error(data.error);
        showStatus(`✅ ${data.nouveaux} nouvelles annonces Sarouty.`, 'success');
        await loadStats();
        await search();
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
    }
}

async function scrapeMubawab() {
    const btn = document.getElementById('btn-scrape-mub');
    const region = document.getElementById('region_mubawab').value;
    btn.disabled = true;
    showStatus(`Scraping Mubawab (${region}) en cours… (max 3 pages)`, 'info');

    try {
        const data = await fetch('/api/scraper_mubawab', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region, max_pages: 3 }),
        }).then(r => r.json());

        if (data.error) throw new Error(data.error);
        showStatus(`✅ ${data.nouveaux} nouvelles annonces Mubawab.`, 'success');
        await loadStats();
        setActiveTab('mubawab');
        await search();
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
    }
}

function buildFilterParams() {
    const params = new URLSearchParams();
    const fields = [
        'source', 'budget_min', 'budget_max', 'ville', 'type_bien',
        'surface_min', 'surface_max', 'prix_m2_min', 'prix_m2_max',
    ];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value) params.append(id, el.value);
    });
    return params;
}