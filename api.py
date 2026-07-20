# api.py
from flask import Flask, request, jsonify, render_template_string
from filters import get_filtered_data, get_statistiques_globales, get_prix_m2_moyen_par_groupe
from config import REGIONS
import asyncio
from scraper.runner import scrape_regions
from scraper.sarouty import scraper_sarouty
from database.db_manager import (
    get_annonces_sarouty_filtered,
    get_types_by_source,
    get_villes_by_source
)
import pandas as pd
import traceback

app = Flask(__name__)

# ---- PAGE HTML INTÉGRÉE (version finale) ----
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🏗️ Analyse immobilière Maroc</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f7fa; }
        h1 { color: #1a5276; }
        .container { max-width: 1400px; margin: auto; }
        .stats { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .filters { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        .filters input, .filters select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        .filters button { padding: 8px 20px; background: #2874a6; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .filters button:hover { background: #1a5276; }
        .filters .btn-scraper { background: #27ae60; }
        .filters .btn-scraper:hover { background: #1e8449; }
        .filters .btn-scraper-sarouty { background: #e67e22; }
        .filters .btn-scraper-sarouty:hover { background: #d35400; }
        .filters .btn-scraper-alomrane { background: #2980b9; }
        .filters .btn-scraper-alomrane:hover { background: #1f618d; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th { background: #2874a6; color: white; padding: 10px; text-align: left; }
        td { padding: 8px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f0f8ff; }
        .prix-m2 { font-weight: bold; color: #1a5276; }
        .badge-promo { background: #f39c12; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .badge-nouveau { background: #2ecc71; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .etage { background: #eaf2f8; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .loading { text-align: center; padding: 20px; color: #7f8c8d; }
        .scraping-status { margin: 10px 0; padding: 10px; background: #fef9e7; border-radius: 4px; display: none; }
        .source-tag { background: #5b8c5a; color: white; padding: 2px 8px; border-radius: 12px; font-size: 10px; }
        .category-select { background: #f0f8ff; }
    </style>
</head>
<body>
<div class="container">
    <h1>🏗️ Analyse des opportunités immobilières (Al Omrane + Sarouty)</h1>

    <div id="stats" class="stats">Chargement des statistiques...</div>

    <!-- Filtres principaux -->
    <div class="filters">
        <label>Source :</label>
        <select id="source">
            <option value="all">Toutes les sources</option>
            <option value="alomrane">Al Omrane</option>
            <option value="sarouty">Sarouty</option>
        </select>

        <input type="number" id="budget_min" placeholder="Budget min (DH)" step="1000">
        <input type="number" id="budget_max" placeholder="Budget max (DH)" step="1000">

        <input type="text" id="ville" placeholder="Ville" list="villes">
        <datalist id="villes"></datalist>

        <select id="type_bien"><option value="">Type</option></select>
        <select id="badge"><option value="">Badge</option></select>
        <select id="etage"><option value="">Étage</option></select>

        <input type="number" id="surface_min" placeholder="Surface min (m²)" step="1">
        <input type="number" id="surface_max" placeholder="Surface max (m²)" step="1">

        <input type="number" id="prix_m2_min" placeholder="Prix/m² min" step="100">
        <input type="number" id="prix_m2_max" placeholder="Prix/m² max" step="100">

        <button onclick="rechercher()">🔍 Rechercher</button>
        <button onclick="reinitialiser()" style="background:#95a5a6;">↺ Réinitialiser</button>
    </div>

    <!-- Barre de scraping -->
    <div class="filters" style="background:#f0f8ff; margin-top:5px; flex-wrap: wrap;">
        <!-- Al Omrane -->
        <label for="region_select">Région Al Omrane :</label>
        <select id="region_select">
            <option value="">Toutes les régions</option>
        </select>
        <button id="btn-scraper" class="btn-scraper-alomrane" onclick="lancerScraping()">🔄 Scraper Al Omrane</button>

        <span style="color:#ccc; margin:0 5px;">|</span>

        <!-- Sarouty -->
        <label for="region_sarouty">Région Sarouty :</label>
        <select id="region_sarouty">
            <option value="all">Toutes</option>
            <option value="casablanca">Casablanca</option>
            <option value="rabat">Rabat</option>
        </select>

        <label for="category_sarouty">Catégorie :</label>
        <select id="category_sarouty" class="category-select">
            <option value="1">Résidentiel</option>
            <option value="2">Commercial</option>
        </select>

        <button id="btn-scraper-sarouty" class="btn-scraper-sarouty" onclick="lancerScrapingSarouty()">🔄 Scraper Sarouty</button>

        <span id="scraping-status" class="scraping-status"></span>
    </div>

    <!-- Résultats -->
    <div id="results">
        <table>
            <thead>
                <tr>
                    <th>Projet</th>
                    <th>Localisation</th>
                    <th>Type</th>
                    <th>Badge</th>
                    <th>Lot</th>
                    <th>Produit</th>
                    <th>Surface</th>
                    <th>Prix</th>
                    <th>Prix/m²</th>
                    <th>Étage</th>
                    <th>Désignation</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody id="table-body">
                <tr><td colspan="12" class="loading">Effectuez une recherche</td></tr>
            </tbody>
        </table>
        <div id="count" style="margin-top:10px; color:#7f8c8d;"></div>
    </div>
</div>

<script>
    // ---- Fonction pour mettre à jour les listes dynamiques ----
    function updateOptions(source) {
        fetch('/api/options?source=' + source)
            .then(r => r.json())
            .then(data => {
                // Mettre à jour la datalist des villes
                const datalist = document.getElementById('villes');
                datalist.innerHTML = '';
                (data.villes || []).forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = v;
                    datalist.appendChild(opt);
                });

                // Mettre à jour le select des types
                const typeSelect = document.getElementById('type_bien');
                const currentType = typeSelect.value;
                typeSelect.innerHTML = '<option value="">Type</option>';
                (data.types || []).forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t;
                    opt.textContent = t;
                    typeSelect.appendChild(opt);
                });
                if (currentType) typeSelect.value = currentType;
            })
            .catch(err => console.error('Erreur chargement options:', err));
    }

    // ---- Chargement initial ----
    fetch('/api/stats')
        .then(r => r.json())
        .then(data => {
            document.getElementById('stats').innerHTML = `
                📊 <b>Projets Al Omrane :</b> ${data.nb_projets} &nbsp;|&nbsp;
                <b>Lots :</b> ${data.nb_lots} &nbsp;|&nbsp;
                <b>Produits :</b> ${data.nb_produits} &nbsp;|&nbsp;
                <b>Annonces Sarouty :</b> ${data.nb_sarouty || 0} &nbsp;|&nbsp;
                <b>Villes :</b> ${(data.villes || []).join(', ')} ${data.villes_sarouty ? ' + ' + (data.villes_sarouty || []).join(', ') : ''}
            `;

            updateOptions('all');

            (data.badges || []).forEach(b => {
                const opt = document.createElement('option');
                opt.value = b;
                opt.textContent = b;
                document.getElementById('badge').appendChild(opt);
            });
            (data.etages || []).forEach(e => {
                const opt = document.createElement('option');
                opt.value = e;
                opt.textContent = e;
                document.getElementById('etage').appendChild(opt);
            });
            (data.regions || []).forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.id;
                opt.textContent = r.nom;
                document.getElementById('region_select').appendChild(opt);
            });
        });

    // ---- Écouteur sur le changement de source ----
    document.getElementById('source').addEventListener('change', function() {
        updateOptions(this.value);
    });

    // ---- Recherche ----
    function rechercher() {
        const params = new URLSearchParams();
        const source = document.getElementById('source').value;
        const bmin = document.getElementById('budget_min').value;
        const bmax = document.getElementById('budget_max').value;
        const ville = document.getElementById('ville').value;
        const type = document.getElementById('type_bien').value;
        const badge = document.getElementById('badge').value;
        const etage = document.getElementById('etage').value;
        const smin = document.getElementById('surface_min').value;
        const smax = document.getElementById('surface_max').value;
        const pm2min = document.getElementById('prix_m2_min').value;
        const pm2max = document.getElementById('prix_m2_max').value;

        if (source) params.append('source', source);
        if (bmin) params.append('budget_min', bmin);
        if (bmax) params.append('budget_max', bmax);
        if (ville) params.append('ville', ville);
        if (type) params.append('type_bien', type);
        if (badge) params.append('badge', badge);
        if (etage) params.append('etage', etage);
        if (smin) params.append('surface_min', smin);
        if (smax) params.append('surface_max', smax);
        if (pm2min) params.append('prix_m2_min', pm2min);
        if (pm2max) params.append('prix_m2_max', pm2max);

        fetch('/api/filtrer?' + params.toString())
            .then(r => r.json())
            .then(data => {
                const tbody = document.getElementById('table-body');
                tbody.innerHTML = '';
                if (!data || data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="12" style="text-align:center;padding:20px;">Aucun résultat</td></tr>';
                    document.getElementById('count').textContent = '0 résultat';
                    return;
                }
                data.forEach(row => {
                    const tr = document.createElement('tr');
                    const badgeClass = row.badge === 'Promotion' ? 'badge-promo' : (row.badge === 'Nouveau' ? 'badge-nouveau' : '');
                    tr.innerHTML = `
                        <td><strong>${row.projet || ''}</strong></td>
                        <td>${row.ville || ''}</td>
                        <td>${row.type_bien || ''}</td>
                        <td>${row.badge ? `<span class="${badgeClass}">${row.badge}</span>` : '-'}</td>
                        <td style="font-size:12px;">${row.lot || '-'}</td>
                        <td>${row.produit || '-'}</td>
                        <td>${row.surface || '-'}</td>
                        <td>${row.prix || '-'}</td>
                        <td class="prix-m2">${row.prix_m2 !== undefined && row.prix_m2 !== null && !isNaN(row.prix_m2) ? row.prix_m2 : '-'}</td>
                        <td>${row.etage ? `<span class="etage">${row.etage}</span>` : '-'}</td>
                        <td style="font-size:12px;">${row.designation || '-'}</td>
                        <td><span class="source-tag">${row.source || '-'}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
                document.getElementById('count').textContent = `${data.length} résultat(s)`;
            })
            .catch(err => {
                console.error('Erreur de recherche:', err);
                document.getElementById('table-body').innerHTML = '<tr><td colspan="12" style="text-align:center;padding:20px;color:red;">Erreur de chargement</td></tr>';
            });
    }

    function reinitialiser() {
        document.getElementById('budget_min').value = '';
        document.getElementById('budget_max').value = '';
        document.getElementById('ville').value = '';
        document.getElementById('type_bien').value = '';
        document.getElementById('badge').value = '';
        document.getElementById('etage').value = '';
        document.getElementById('surface_min').value = '';
        document.getElementById('surface_max').value = '';
        document.getElementById('prix_m2_min').value = '';
        document.getElementById('prix_m2_max').value = '';
        document.getElementById('source').value = 'all';
        updateOptions('all');
        rechercher();
    }

    // ---- Scraping Al Omrane ----
    function lancerScraping() {
        const regionSelect = document.getElementById('region_select');
        const regionId = regionSelect.value;
        const statusDiv = document.getElementById('scraping-status');
        const btn = document.getElementById('btn-scraper');

        if (!regionId) {
            alert('Veuillez sélectionner une région.');
            return;
        }

        btn.disabled = true;
        statusDiv.style.display = 'block';
        statusDiv.innerHTML = '⏳ Scraping Al Omrane en cours...';
        statusDiv.style.background = '#fef9e7';

        fetch('/api/scraper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ region_ids: [parseInt(regionId)], deep: false, limit_pages: null })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                statusDiv.innerHTML = '❌ Erreur : ' + data.error;
                statusDiv.style.background = '#f2dede';
            } else {
                statusDiv.innerHTML = `✅ ${data.message} — ${data.nouveaux_projets} nouveaux projets trouvés.`;
                if (data.nouveaux_projets > 0) {
                    statusDiv.innerHTML += '<br>Liste : ' + data.projets.map(p => p.titre + ' (' + p.localisation + ')').join(', ');
                }
                statusDiv.style.background = '#d5f5e3';
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(statsData => {
                        document.getElementById('stats').innerHTML = `
                            📊 <b>Projets Al Omrane :</b> ${statsData.nb_projets} &nbsp;|&nbsp;
                            <b>Lots :</b> ${statsData.nb_lots} &nbsp;|&nbsp;
                            <b>Produits :</b> ${statsData.nb_produits} &nbsp;|&nbsp;
                            <b>Annonces Sarouty :</b> ${statsData.nb_sarouty || 0} &nbsp;|&nbsp;
                            <b>Villes :</b> ${(statsData.villes || []).join(', ')} ${statsData.villes_sarouty ? ' + ' + (statsData.villes_sarouty || []).join(', ') : ''}
                        `;
                    });
                updateOptions(document.getElementById('source').value);
                rechercher();
            }
        })
        .catch(err => {
            statusDiv.innerHTML = '❌ Erreur : ' + err;
            statusDiv.style.background = '#f2dede';
        })
        .finally(() => {
            btn.disabled = false;
        });
    }

    // ---- Scraping Sarouty ----
    function lancerScrapingSarouty() {
        const statusDiv = document.getElementById('scraping-status');
        const btn = document.getElementById('btn-scraper-sarouty');
        const regionSelect = document.getElementById('region_sarouty');
        const region = regionSelect.value;
        const categorySelect = document.getElementById('category_sarouty');
        const category = categorySelect.value;

        btn.disabled = true;
        statusDiv.style.display = 'block';
        statusDiv.innerHTML = '⏳ Scraping Sarouty en cours... (max 5 pages)';
        statusDiv.style.background = '#fef9e7';

        fetch('/api/scraper_sarouty', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_pages: 5, region: region, category: category })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                statusDiv.innerHTML = '❌ Erreur : ' + data.error;
                statusDiv.style.background = '#f2dede';
            } else {
                statusDiv.innerHTML = `✅ ${data.message} — ${data.nouveaux} nouvelles annonces.`;
                statusDiv.style.background = '#d5f5e3';
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(statsData => {
                        document.getElementById('stats').innerHTML = `
                            📊 <b>Projets Al Omrane :</b> ${statsData.nb_projets} &nbsp;|&nbsp;
                            <b>Lots :</b> ${statsData.nb_lots} &nbsp;|&nbsp;
                            <b>Produits :</b> ${statsData.nb_produits} &nbsp;|&nbsp;
                            <b>Annonces Sarouty :</b> ${statsData.nb_sarouty || 0} &nbsp;|&nbsp;
                            <b>Villes :</b> ${(statsData.villes || []).join(', ')} ${statsData.villes_sarouty ? ' + ' + (statsData.villes_sarouty || []).join(', ') : ''}
                        `;
                    });
                updateOptions(document.getElementById('source').value);
                rechercher();
            }
        })
        .catch(err => {
            statusDiv.innerHTML = '❌ Erreur : ' + err;
            statusDiv.style.background = '#f2dede';
        })
        .finally(() => {
            btn.disabled = false;
        });
    }

    // Lancer la recherche au chargement
    window.onload = function() {
        setTimeout(rechercher, 500);
    };
</script>
</body>
</html>
"""

# ---- ROUTES ----
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/options', methods=['GET'])
def options():
    source = request.args.get('source', 'all')
    try:
        types = get_types_by_source(source)
        villes = get_villes_by_source(source)
        return jsonify({'types': types, 'villes': villes})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/filtrer', methods=['GET'])
def filtrer():
    args = request.args
    try:
        print(f"🔍 Filtrage reçu : {args.to_dict()}")  # Log pour debug
        df = get_filtered_data(
            source=args.get('source', 'all'),
            budget_min=float(args.get('budget_min')) if args.get('budget_min') and args.get('budget_min') != '' else None,
            budget_max=float(args.get('budget_max')) if args.get('budget_max') and args.get('budget_max') != '' else None,
            ville=args.get('ville'),
            type_bien=args.get('type_bien'),
            badge=args.get('badge'),
            etage=args.get('etage'),
            prix_m2_min=float(args.get('prix_m2_min')) if args.get('prix_m2_min') and args.get('prix_m2_min') != '' else None,
            prix_m2_max=float(args.get('prix_m2_max')) if args.get('prix_m2_max') and args.get('prix_m2_max') != '' else None,
            surface_min=float(args.get('surface_min')) if args.get('surface_min') and args.get('surface_min') != '' else None,
            surface_max=float(args.get('surface_max')) if args.get('surface_max') and args.get('surface_max') != '' else None,
            limit=int(args.get('limit')) if args.get('limit') else None
        )
        df = df.where(pd.notnull(df), None)
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/stats', methods=['GET'])
def stats():
    try:
        stats = get_statistiques_globales()
        stats['regions'] = [{'id': r['id'], 'nom': r['nom']} for r in REGIONS]
        return jsonify(stats)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/scraper', methods=['POST'])
def scraper():
    data = request.get_json()
    region_ids = data.get('region_ids', [])
    deep = data.get('deep', False)
    limit_pages = data.get('limit_pages', None)

    if not region_ids:
        return jsonify({'error': 'Aucune région sélectionnée'}), 400

    valid_ids = [r['id'] for r in REGIONS]
    invalid = [id for id in region_ids if id not in valid_ids]
    if invalid:
        return jsonify({'error': f'Région(s) invalide(s) : {invalid}'}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        projets = loop.run_until_complete(
            scrape_regions(region_ids, headless=True, limit_pages=limit_pages, deep_scrape=deep)
        )
    finally:
        loop.close()

    return jsonify({
        'message': f'Scraping terminé pour les régions {region_ids}',
        'nouveaux_projets': len(projets),
        'projets': [{
            'titre': p['titre'],
            'localisation': p['localisation'],
            'type_bien': p['type_bien'],
            'badge': p['badge']
        } for p in projets]
    })

@app.route('/api/scraper_sarouty', methods=['POST'])
def scraper_sarouty_endpoint():
    data = request.get_json() or {}
    max_pages = data.get('max_pages', 5)
    region = data.get('region')
    category = data.get('category', '1')  # '1' résidentiel, '2' commercial

    if region == 'casablanca':
        region_ids = [35]
    elif region == 'rabat':
        region_ids = [113]
    else:
        region_ids = [35, 113]

    try:
        nb = scraper_sarouty(max_pages=max_pages, region_ids=region_ids, category=category)
        return jsonify({'message': 'Scraping Sarouty terminé.', 'nouveaux': nb})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sarouty/filtrer', methods=['GET'])
def filtrer_sarouty():
    args = request.args
    filters = {
        'ville': args.get('ville'),
        'type_bien': args.get('type_bien'),
        'budget_min': float(args.get('budget_min')) if args.get('budget_min') and args.get('budget_min') != '' else None,
        'budget_max': float(args.get('budget_max')) if args.get('budget_max') and args.get('budget_max') != '' else None,
        'superficie_min': float(args.get('superficie_min')) if args.get('superficie_min') and args.get('superficie_min') != '' else None,
        'superficie_max': float(args.get('superficie_max')) if args.get('superficie_max') and args.get('superficie_max') != '' else None,
        'prix_m2_min': float(args.get('prix_m2_min')) if args.get('prix_m2_min') and args.get('prix_m2_min') != '' else None,
        'prix_m2_max': float(args.get('prix_m2_max')) if args.get('prix_m2_max') and args.get('prix_m2_max') != '' else None,
    }
    data = get_annonces_sarouty_filtered(**filters)
    return jsonify(data)

@app.route('/api/moyennes', methods=['GET'])
def moyennes():
    args = request.args
    try:
        df = get_prix_m2_moyen_par_groupe(
            ville=args.get('ville'),
            type_bien=args.get('type_bien'),
            etage=args.get('etage')
        )
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)