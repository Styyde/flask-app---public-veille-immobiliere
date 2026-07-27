// tables.js – Version simplifiée : Al Omrane en table unique (produits à plat)

function renderSarouty(rows) {
    const tbody = document.getElementById('tbody-sarouty');
    document.getElementById('count-sar').textContent = rows.length;

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Aucune annonce Sarouty pour ces filtres</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(row => `
        <tr>
            <td><strong>${fmt(row.projet)}</strong></td>
            <td>${fmt(row.localisation)}</td>
            <td>${fmt(row.type)}</td>
            <td>${formatSurface(row.surface)}</td>
            <td>${formatPrix(row.prix)}</td>
            <td class="prix-m2">${formatPrixM2(row.prix_m2)}</td>
            <td>
                ${row.url_annonce
                    ? `<button class="btn btn-sm btn-consult" data-url="${escapeAttr(row.url_annonce)}">Accéder</button>`
                    : '—'}
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });
}

function renderMubawab(rows) {
    const tbody = document.getElementById('tbody-mubawab');
    document.getElementById('count-mub').textContent = rows.length;

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Aucune annonce Mubawab pour ces filtres</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(row => `
        <tr>
            <td><strong>${fmt(row.projet)}</strong></td>
            <td>${fmt(row.localisation)}</td>
            <td>${fmt(row.type)}</td>
            <td>${formatSurface(row.surface)}</td>
            <td>${formatPrix(row.prix)}</td>
            <td class="prix-m2">${formatPrixM2(row.prix_m2)}</td>
            <td>
                ${row.url_annonce
                    ? `<button class="btn btn-sm btn-consult" data-url="${escapeAttr(row.url_annonce)}">Accéder</button>`
                    : '—'}
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });
}

function escapeAttr(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}

/* ==================== AL OMRANE – TABLE UNIQUE (PRODUITS À PLAT) ==================== */

function renderAlomrane(rows) {
    const container = document.getElementById('alomrane-list');
    document.getElementById('count-ao').textContent = rows.length;

    if (!rows.length) {
        container.innerHTML = '<div class="empty-state">Aucun produit Al Omrane pour ces filtres</div>';
        return;
    }

    let html = `
        <div class="table-wrap">
            <table class="data-table" id="table-alomrane">
                <thead>
                    <tr>
                        <th>Projet</th>
                        <th>Localisation</th>
                        <th>Lot</th>
                        <th>Produit</th>
                        <th>Surface</th>
                        <th>Prix</th>
                        <th>Prix/m²</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;

    rows.forEach(row => {
        const projet = fmt(row.projet);
        const localisation = fmt(row.ville);
        const lot = fmt(row.lot);
        const produit = fmt(row.produit);
        const surface = formatSurface(row.surface);
        const prix = formatPrix(row.prix);
        const prix_m2 = formatPrixM2(row.prix_m2);
        const url = row.url_produit || row.url_projet;

        html += `
            <tr>
                <td><strong>${projet}</strong></td>
                <td>${localisation}</td>
                <td>${lot}</td>
                <td>${produit}</td>
                <td>${surface}</td>
                <td>${prix}</td>
                <td class="prix-m2">${prix_m2}</td>
                <td>
                    ${url
                        ? `<button class="btn btn-sm btn-consult" data-url="${escapeAttr(url)}">Accéder</button>`
                        : '—'}
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;

    container.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });
}

// =====================================================
// Anciennes fonctions d'expansion (conservées commentées pour référence)
// Elles ne sont plus utilisées avec la nouvelle version.
// =====================================================

/*
const expandedProjects = new Set();
const expandedLots = new Set();

async function toggleProject(id) {
    const row = document.querySelector(`tr.project-row[data-project-id="${id}"]`);
    const detailRow = document.getElementById(`detail-row-${id}`);
    const btn = document.querySelector(`.btn-detail[data-id="${id}"]`);
    if (!detailRow || !row || !btn) return;

    if (expandedProjects.has(id)) {
        expandedProjects.delete(id);
        detailRow.style.display = 'none';
        row.classList.remove('expanded');
        btn.textContent = 'Détails';
    } else {
        expandedProjects.add(id);
        detailRow.style.display = 'table-row';
        row.classList.add('expanded');
        btn.textContent = 'Masquer';
        await loadProjectDetail(id);
    }
}

async function loadProjectDetail(id) {
    const panel = document.getElementById(`detail-panel-${id}`);
    if (!panel) return;
    if (panel.dataset.loaded === 'true') return;
    panel.innerHTML = '<div class="yt-loading">Chargement des lots…</div>';
    try {
        const projet = await fetchJSON(`/api/alomrane/projets/${id}`);
        panel.innerHTML = renderHierarchyHTML(projet);
        panel.dataset.loaded = 'true';
        bindLotToggles(panel, id);
        bindConsultButtons(panel);
    } catch (err) {
        panel.innerHTML = `<div class="yt-error">Erreur : ${err.message}</div>`;
    }
}

function bindConsultButtons(root) {
    root.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });
}

function bindLotToggles(panel, projetId) {
    panel.querySelectorAll('.yt-lot-header').forEach(header => {
        header.addEventListener('click', (e) => {
            if (e.target.closest('.btn-consult')) return;
            const lotId = header.dataset.lotId;
            const key = `${projetId}-${lotId}`;
            const body = panel.querySelector(`#lot-body-${projetId}-${lotId}`);
            const chevron = header.querySelector('.yt-chevron');
            if (!body) return;
            if (expandedLots.has(key)) {
                expandedLots.delete(key);
                body.style.display = 'none';
                header.classList.remove('is-open');
                chevron?.classList.remove('open');
            } else {
                expandedLots.add(key);
                body.style.display = 'block';
                header.classList.add('is-open');
                chevron?.classList.add('open');
            }
        });
    });
}

function renderHierarchyHTML(projet) {
    if (!projet.lots || !projet.lots.length) {
        return '<div class="empty-state">Aucun lot disponible</div>';
    }
    return `
    <div class="yt-hierarchy">
        <div class="yt-breadcrumb">Projet <span>›</span> Lots <span>›</span> Produits</div>
        ${projet.lots.map(lot => {
            const key = `${projet.id}-${lot.id}`;
            const isOpen = expandedLots.has(key) || projet.lots.length === 1;
            if (projet.lots.length === 1) expandedLots.add(key);
            const produits = lot.lignes || [];
            return `
            <div class="yt-lot ${isOpen ? 'is-open' : ''}">
                <div class="yt-lot-header ${isOpen ? 'is-open' : ''}" data-lot-id="${lot.id}">
                    <button class="yt-chevron ${isOpen ? 'open' : ''}" aria-label="Développer le lot">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/></svg>
                    </button>
                    <div class="yt-lot-info">
                        <div class="yt-lot-title">${fmt(lot.lot_titre)}</div>
                        <div class="yt-lot-meta">
                            ${fmt(lot.nb_unites)}
                            ${lot.prix_min ? ` · ${fmt(lot.prix_min)} – ${fmt(lot.prix_max)}` : ''}
                            · ${produits.length} produit${produits.length > 1 ? 's' : ''}
                        </div>
                    </div>
                </div>
                <div class="yt-lot-body" id="lot-body-${projet.id}-${lot.id}" style="display:${isOpen ? 'block' : 'none'}">
                    ${produits.length ? renderProduitsTable(produits, projet) : '<div class="empty-state">Aucun produit</div>'}
                </div>
            </div>`;
        }).join('')}
    </div>`;
}

function renderProduitsTable(produits, projet) {
    return `
    <div class="yt-products-wrap">
        <table class="yt-products">
            <thead>
                <tr>
                    <th>Produit</th>
                    <th>Surface</th>
                    <th>Prix</th>
                    <th>Prix/m²</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${produits.map(l => `
                    <tr>
                        <td class="prod-id">${fmt(l.no_produit)}</td>
                        <td>${formatSurface(l.surface)}</td>
                        <td>${formatPrix(l.prix)}</td>
                        <td class="prix-m2">${formatPrixM2(l.prix_m2)}</td>
                        <td>
                            ${(l.url || projet.url)
                                ? `<button class="btn btn-sm btn-consult" data-url="${escapeAttr(l.url || projet.url)}">Accéder</button>`
                                : '—'}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    </div>`;
}
*/