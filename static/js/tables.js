// static/js/tables.js
const expandedProjects = new Set();
const expandedLots = new Set();
let favorisSet = new Set();

async function refreshFavorisSet() {
    try {
        const data = await fetchJSON('/api/favoris');
        favorisSet = new Set(data.map(f => `${f.source}:${String(f.annonce_id)}`));
    } catch {
        favorisSet = new Set();
    }
    return favorisSet;
}

function isFavori(source, annonceId) {
    if (annonceId === null || annonceId === undefined || annonceId === '') return false;
    return favorisSet.has(`${source}:${String(annonceId)}`);
}

function buildFavButton(source, annonceId, attrs) {
    const active = isFavori(source, annonceId);
    const disabled = active ? 'disabled' : '';
    const cls = active ? 'btn btn-sm btn-fav is-active' : 'btn btn-sm btn-fav';
    const label = active ? '★ Favori' : '⭐ Ajouter';
    return `
        <button class="${cls}" ${disabled}
                data-source="${escapeAttr(source)}"
                data-annonce-id="${escapeAttr(String(annonceId))}"
                data-url="${escapeAttr(attrs.url || '')}"
                data-titre="${escapeAttr(attrs.titre || '')}"
                data-localisation="${escapeAttr(attrs.localisation || '')}"
                data-type="${escapeAttr(attrs.type || '')}"
                data-surface="${escapeAttr(attrs.surface ?? '')}"
                data-prix="${escapeAttr(attrs.prix ?? '')}"
                data-prix-m2="${attrs.prix_m2 ?? ''}">
            ${label}
        </button>`;
}

function renderSarouty(rows) {
    const tbody = document.getElementById('tbody-sarouty');
    document.getElementById('count-sar').textContent = rows.length;

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty">Aucune annonce Sarouty pour ces filtres</td></tr>';
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
            <td>
                ${buildFavButton('sarouty', row.property_id, {
                    url: row.url_annonce,
                    titre: row.projet,
                    localisation: row.localisation,
                    type: row.type,
                    surface: row.surface,
                    prix: row.prix,
                    prix_m2: row.prix_m2,
                })}
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });

    bindFavButtons(tbody);
}

function renderMubawab(rows) {
    const tbody = document.getElementById('tbody-mubawab');
    document.getElementById('count-mub').textContent = rows.length;

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty">Aucune annonce Mubawab pour ces filtres</td></tr>';
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
            <td>
                ${buildFavButton('mubawab', row.id, {
                    url: row.url_annonce,
                    titre: row.projet,
                    localisation: row.localisation,
                    type: row.type,
                    surface: row.surface,
                    prix: row.prix,
                    prix_m2: row.prix_m2,
                })}
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });

    bindFavButtons(tbody);
}

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
                        <th>Favoris</th>
                    </tr>
                </thead>
                <tbody>
    `;

    rows.forEach(row => {
        const url = row.url_produit || row.url_projet;
        const annonceId = row.produit_id;
        html += `
            <tr>
                <td><strong>${fmt(row.projet)}</strong></td>
                <td>${fmt(row.ville)}</td>
                <td>${fmt(row.lot)}</td>
                <td>${fmt(row.produit)}</td>
                <td>${formatSurface(row.surface)}</td>
                <td>${formatPrix(row.prix)}</td>
                <td class="prix-m2">${formatPrixM2(row.prix_m2)}</td>
                <td>
                    ${url
                        ? `<button class="btn btn-sm btn-consult" data-url="${escapeAttr(url)}">Accéder</button>`
                        : '—'}
                </td>
                <td>
                    ${annonceId != null
                        ? buildFavButton('alomrane', annonceId, {
                            url,
                            titre: row.projet,
                            localisation: row.ville,
                            type: row.type_bien,
                            surface: row.surface,
                            prix: row.prix,
                            prix_m2: row.prix_m2,
                        })
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

    bindFavButtons(container);

    container.querySelectorAll('.btn-consult').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openUrl(btn.dataset.url);
        });
    });
}

function bindFavButtons(container) {
    container.querySelectorAll('.btn-fav:not(.is-active)').forEach(btn => {
        btn.addEventListener('click', handleFavClick);
    });
}

async function handleFavClick(e) {
    const btn = e.currentTarget;
    if (btn.classList.contains('is-active')) return;

    btn.disabled = true;

    const data = {
        source: btn.dataset.source,
        annonce_id: btn.dataset.annonceId,
        url: btn.dataset.url,
        titre: btn.dataset.titre,
        localisation: btn.dataset.localisation,
        type_bien: btn.dataset.type,
        surface: btn.dataset.surface,
        prix: btn.dataset.prix,
        prix_m2: parseFloat(btn.dataset.prixM2) || null,
    };

    try {
        const response = await fetch('/api/favoris', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();
        if (response.ok) {
            favorisSet.add(`${data.source}:${String(data.annonce_id)}`);
            btn.textContent = '★ Favori';
            btn.classList.add('is-active');
            if (typeof window.refreshFavoris === 'function') {
                window.refreshFavoris();
            }
        } else {
            alert('Erreur : ' + (result.error || result.message));
            btn.disabled = false;
        }
    } catch (err) {
        alert('Erreur réseau : ' + err.message);
        btn.disabled = false;
    }
}

function escapeAttr(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}

window.refreshFavorisSet = refreshFavorisSet;
