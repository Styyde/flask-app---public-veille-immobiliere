let activeTab = 'alomrane';

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initFilters();
    loadStats();
    loadFavoris();
    document.getElementById('btn-search').addEventListener('click', search);
    document.getElementById('btn-reset').addEventListener('click', resetFilters);
    document.getElementById('btn-scrape-ao').addEventListener('click', scrapeAlomrane);
    document.getElementById('btn-scrape-sar').addEventListener('click', scrapeSarouty);
    document.getElementById('btn-scrape-mub').addEventListener('click', scrapeMubawab);
    document.getElementById('source').addEventListener('change', onSourceChange);
    
    // Sidebar logic
    const toggleBtn = document.getElementById('btn-toggle-scrape');
    const closeBtn = document.getElementById('btn-close-scrape');
    const sidebar = document.getElementById('scrape-sidebar');
    const overlay = document.getElementById('scrape-overlay');
    
    const openSidebar = () => { sidebar.classList.add('open'); overlay.classList.add('open'); };
    const closeSidebar = () => { sidebar.classList.remove('open'); overlay.classList.remove('open'); };
    
    if(toggleBtn) toggleBtn.addEventListener('click', openSidebar);
    if(closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if(overlay) overlay.addEventListener('click', closeSidebar);
    
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
            if (activeTab === 'favoris') {
                loadFavoris();
            }
        });
    });
}

function initFilters() {
    onSourceChange();
}

function onSourceChange() {
    const source = document.getElementById('source').value;
    updateOptions(source);
    if (activeTab === 'favoris') return;
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
        document.getElementById('count-fav').textContent = data.nb_favoris || 0;
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
        { label: '⭐ Favoris', value: data.nb_favoris || 0 },
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
        '<tr><td colspan="8" class="empty">Chargement…</td></tr>';
    document.getElementById('tbody-mubawab').innerHTML =
        '<tr><td colspan="8" class="empty">Chargement…</td></tr>';

    if (typeof refreshFavorisSet === 'function') {
        await refreshFavorisSet();
    }

    const promises = [];
    const loadAo = source === 'all' || source === 'alomrane';
    const loadSar = source === 'all' || source === 'sarouty';
    const loadMub = source === 'all' || source === 'mubawab';

    if (loadAo) {
        const p = new URLSearchParams(params);
        p.delete('source');
        promises.push(
            fetchJSON(`/api/alomrane/produits?${p}`).then(renderAlomrane).catch(e => {
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
                    `<tr><td colspan="8" class="empty" style="color:red">${e.message}</td></tr>`;
            })
        );
    } else {
        document.getElementById('tbody-sarouty').innerHTML =
            '<tr><td colspan="8" class="empty">Autre source sélectionnée</td></tr>';
        document.getElementById('count-sar').textContent = '0';
    }

    if (loadMub) {
        const p = new URLSearchParams(params);
        p.delete('source');
        promises.push(
            fetchJSON(`/api/mubawab/annonces?${p}`).then(renderMubawab).catch(e => {
                document.getElementById('tbody-mubawab').innerHTML =
                    `<tr><td colspan="8" class="empty" style="color:red">${e.message}</td></tr>`;
            })
        );
    } else {
        document.getElementById('tbody-mubawab').innerHTML =
            '<tr><td colspan="8" class="empty">Autre source sélectionnée</td></tr>';
        document.getElementById('count-mub').textContent = '0';
    }

    promises.push(
        fetchJSON(`/api/analytics?${params}`).then(renderCharts).catch(console.error)
    );

    await Promise.all(promises);
    syncFavorisCount();
}

function syncFavorisCount() {
    fetchJSON('/api/favoris').then(data => {
        document.getElementById('count-fav').textContent = data.length;
    }).catch(() => {});
}

function resetFilters() {
    if (activeTab === 'favoris') {
        loadFavoris();
        return;
    }
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

async function pollTask(taskId, btn, successMessageBuilder) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/api/scraper/status/${taskId}`);
            const data = await res.json();
            
            if (data.error) {
                clearInterval(interval);
                showStatus(`❌ ${data.error}`, 'error');
                btn.disabled = false;
                return;
            }
            
            if (data.status === 'en_cours') {
                showStatus(`⏳ ${data.message || 'En cours...'}`, 'info');
            } else if (data.status === 'termine') {
                clearInterval(interval);
                let msg = data.message;
                if (successMessageBuilder && data.result) {
                    msg = successMessageBuilder(data.result);
                }
                showStatus(`✅ ${msg}`, 'success');
                btn.disabled = false;
                await loadStats();
                await search();
            } else if (data.status === 'erreur') {
                clearInterval(interval);
                showStatus(`❌ ${data.message}`, 'error');
                btn.disabled = false;
            }
        } catch (err) {
            clearInterval(interval);
            showStatus(`❌ Erreur de connexion: ${err.message}`, 'error');
            btn.disabled = false;
        }
    }, 2000);
}

async function scrapeAlomrane() {
    const regionId = document.getElementById('region_select').value;
    const btn = document.getElementById('btn-scrape-ao');
    if (!regionId) { alert('Veuillez sélectionner une région.'); return; }

    btn.disabled = true;
    showStatus('Démarrage Scraping Al Omrane...', 'info');

    try {
        const data = await fetch('/api/scraper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region_ids: [parseInt(regionId)], deep: false }),
        }).then(r => r.json());

        if (data.error) throw new Error(data.error);
        pollTask(data.task_id, btn, (res) => `${res.length} nouveaux projets trouvés.`);
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'error');
        btn.disabled = false;
    }
}

async function scrapeSarouty() {
    const btn = document.getElementById('btn-scrape-sar');
    btn.disabled = true;
    showStatus('Démarrage Scraping Sarouty...', 'info');

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
        pollTask(data.task_id, btn, (res) => `${res} nouvelles annonces Sarouty.`);
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'error');
        btn.disabled = false;
    }
}

async function scrapeMubawab() {
    const btn = document.getElementById('btn-scrape-mub');
    const region = document.getElementById('region_mubawab').value;
    btn.disabled = true;
    showStatus(`Démarrage Scraping Mubawab (${region})...`, 'info');

    try {
        const data = await fetch('/api/scraper_mubawab', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region, max_pages: 3 }),
        }).then(r => r.json());

        if (data.error) throw new Error(data.error);
        
        // Custom polling callback to switch tab for mubawab
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/scraper/status/${data.task_id}`);
                const statusData = await res.json();
                if (statusData.status === 'en_cours') {
                    showStatus(`⏳ ${statusData.message || 'En cours...'}`, 'info');
                } else if (statusData.status === 'termine') {
                    clearInterval(interval);
                    showStatus(`✅ ${statusData.result || 0} nouvelles annonces Mubawab.`, 'success');
                    btn.disabled = false;
                    await loadStats();
                    setActiveTab('mubawab');
                    await search();
                } else if (statusData.status === 'erreur') {
                    clearInterval(interval);
                    showStatus(`❌ ${statusData.message}`, 'error');
                    btn.disabled = false;
                }
            } catch (err) {
                clearInterval(interval);
                showStatus(`❌ Erreur: ${err.message}`, 'error');
                btn.disabled = false;
            }
        }, 2000);
        
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'error');
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
        if (el && el.value) {
            const cleaned = el.value.replace(/\s/g, '').replace(',', '.');
            params.append(id, cleaned);
        }
    });
    return params;
}

// ---------- FAVORIS ----------

async function loadFavoris() {
    try {
        const data = await fetchJSON('/api/favoris');
        renderFavoris(data);
        document.getElementById('count-fav').textContent = data.length;
        if (typeof refreshFavorisSet === 'function') {
            favorisSet = new Set(data.map(f => `${f.source}:${String(f.annonce_id)}`));
        }
    } catch (err) {
        document.getElementById('tbody-favoris').innerHTML =
            `<tr><td colspan="8" class="empty" style="color:red">Erreur : ${err.message}</td></tr>`;
    }
}

function renderFavoris(rows) {
    const tbody = document.getElementById('tbody-favoris');
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty">Aucun favori — utilisez ⭐ Ajouter sur une annonce</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(row => `
        <tr>
            <td>${fmt(row.source)}</td>
            <td><strong>${fmt(row.titre)}</strong></td>
            <td>${fmt(row.localisation)}</td>
            <td>${fmt(row.type_bien)}</td>
            <td>${formatSurface(row.surface)}</td>
            <td>${formatPrix(row.prix)}</td>
            <td class="prix-m2">${formatPrixM2(row.prix_m2)}</td>
            <td class="fav-actions">
                ${row.url
                    ? `<button class="btn btn-sm btn-consult" data-url="${escapeAttr(row.url)}">Accéder</button>`
                    : ''}
                <button class="btn btn-sm btn-remove-fav"
                        data-source="${escapeAttr(row.source)}"
                        data-annonce-id="${escapeAttr(String(row.annonce_id))}">
                    Retirer
                </button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });

    tbody.querySelectorAll('.btn-remove-fav').forEach(btn => {
        btn.addEventListener('click', () => removeFavori(btn));
    });
}

async function removeFavori(btn) {
    const source = btn.dataset.source;
    const annonceId = btn.dataset.annonceId;
    btn.disabled = true;

    try {
        const qs = new URLSearchParams({ source, annonce_id: annonceId });
        const res = await fetch(`/api/favoris?${qs}`, { method: 'DELETE' });
        if (res.ok) {
            if (typeof favorisSet !== 'undefined') {
                favorisSet.delete(`${source}:${annonceId}`);
            }
            await loadFavoris();
            if (typeof refreshFavorisSet === 'function') {
                await refreshFavorisSet();
            }
            if (activeTab !== 'favoris') {
                search();
            }
        } else {
            const result = await res.json();
            alert('Erreur : ' + (result.error || result.message));
            btn.disabled = false;
        }
    } catch (err) {
        alert('Erreur réseau : ' + err.message);
        btn.disabled = false;
    }
}

function refreshFavoris() {
    loadFavoris();
    if (typeof refreshFavorisSet === 'function') {
        refreshFavorisSet();
    }
}

window.refreshFavoris = refreshFavoris;