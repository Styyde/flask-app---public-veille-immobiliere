# api/app.py
import asyncio
import traceback
import uuid
import os
import sqlite3

from flask import Flask, request, jsonify, render_template
from prometheus_flask_exporter import PrometheusMetrics

from config import REGIONS, DB_PATH
from core.runner import scrape_regions
from core.sarouty import scraper_sarouty
from core.mubawab_scraper_single import scraper_mubawab_sync
from database.db_manager import (
    get_projet_detail,
    get_statistiques_globales,
    init_db,
    ajouter_favori,
    supprimer_favori,
    get_favoris,
    est_favori,
    create_task,
    get_task_status
)
from services.task_service import start_scraping_task
from services.filter_service import (
    parse_filtres_from_request,
    filtrer_alomrane,
    filtrer_produits,
    filtrer_sarouty,
    filtrer_mubawab,
    get_filtres_disponibles,
    get_prix_m2_moyen_par_groupe,
)
from services.analysis_service import get_analytics_dashboard

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'), static_folder=os.path.join(base_dir, 'static'))
init_db()

# ---- AJOUT : Métriques Prometheus ----
metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info('app_info', 'Application info', version='1.0.0')
# -------------------------------------

# ---- AJOUT : Endpoint /health ----
@app.route('/health', methods=['GET'])
def health_check():
    """Vérifie l'état de l'application et de la base de données."""
    status = {
        'status': 'healthy',
        'database': 'ok',
        'version': '1.0.0'
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('SELECT 1')
        conn.close()
    except Exception as e:
        status['status'] = 'unhealthy'
        status['database'] = f'error: {str(e)}'
        return jsonify(status), 503
    return jsonify(status), 200
# ----------------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def stats():
    try:
        data = get_statistiques_globales()
        data['regions'] = [{'id': r['id'], 'nom': r['nom']} for r in REGIONS]
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/options', methods=['GET'])
def options():
    source = request.args.get('source', 'all')
    try:
        return jsonify(get_filtres_disponibles(source))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/alomrane/projets', methods=['GET'])
def alomrane_projets():
    try:
        filtres = parse_filtres_from_request(request.args)
        data = filtrer_alomrane(**filtres)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/alomrane/produits', methods=['GET'])
def alomrane_produits():
    try:
        filtres = parse_filtres_from_request(request.args)
        data = filtrer_produits(**filtres)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/alomrane/projets/<int:projet_id>', methods=['GET'])
def alomrane_projet_detail(projet_id):
    try:
        projet = get_projet_detail(projet_id)
        if not projet:
            return jsonify({'error': 'Projet introuvable'}), 404
        return jsonify(projet)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/sarouty/annonces', methods=['GET'])
def sarouty_annonces():
    try:
        filtres = parse_filtres_from_request(request.args)
        return jsonify(filtrer_sarouty(**filtres))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/sarouty/filtrer', methods=['GET'])
def sarouty_filtrer_alias():
    return sarouty_annonces()

@app.route('/api/mubawab/annonces', methods=['GET'])
def mubawab_annonces():
    try:
        filtres = parse_filtres_from_request(request.args)
        return jsonify(filtrer_mubawab(**filtres))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/analytics', methods=['GET'])
def analytics():
    try:
        filtres = parse_filtres_from_request(request.args)
        return jsonify(get_analytics_dashboard(filtres))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/moyennes', methods=['GET'])
def moyennes():
    try:
        data = get_prix_m2_moyen_par_groupe(
            ville=request.args.get('ville'),
            type_bien=request.args.get('type_bien'),
        )
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/filtrer', methods=['GET'])
def filtrer_legacy():
    from services.filter_service import get_filtered_data
    import pandas as pd
    try:
        filtres = parse_filtres_from_request(request.args)
        source = filtres.pop('source', 'all')
        df = get_filtered_data(source=source, **filtres)
        df = df.where(pd.notnull(df), None)
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/api/scraper', methods=['POST'])
def scraper():
    data = request.get_json() or {}
    region_ids = data.get('region_ids', [])
    deep = data.get('deep', False)
    limit_pages = data.get('limit_pages')

    if not region_ids:
        return jsonify({'error': 'Aucune région sélectionnée'}), 400

    valid_ids = [r['id'] for r in REGIONS]
    invalid = [rid for rid in region_ids if rid not in valid_ids]
    if invalid:
        return jsonify({'error': f'Région(s) invalide(s) : {invalid}'}), 400

    task_id = str(uuid.uuid4())
    create_task(task_id, "Al Omrane", f"Démarrage scraping pour régions {region_ids}...")
    
    start_scraping_task(
        task_id, 
        "Al Omrane", 
        True,  # is_async
        scrape_regions, 
        region_ids, 
        headless=True, 
        limit_pages=limit_pages, 
        deep_scrape=deep
    )

    return jsonify({
        'message': 'Scraping Al Omrane lancé en arrière-plan',
        'task_id': task_id
    })

@app.route('/api/scraper_sarouty', methods=['POST'])
def scraper_sarouty_endpoint():
    data = request.get_json() or {}
    max_pages = data.get('max_pages', 5)
    region = data.get('region')
    category = data.get('category', '1')

    if region == 'casablanca':
        region_ids = [35]
    elif region == 'rabat':
        region_ids = [113]
    else:
        region_ids = [35, 113]

    task_id = str(uuid.uuid4())
    create_task(task_id, "Sarouty", "Démarrage scraping Sarouty...")
    
    start_scraping_task(
        task_id,
        "Sarouty",
        False, # is_async
        scraper_sarouty,
        max_pages=max_pages, 
        region_ids=region_ids, 
        category=category
    )
    
    return jsonify({
        'message': 'Scraping Sarouty lancé en arrière-plan.', 
        'task_id': task_id
    })

@app.route('/api/scraper_mubawab', methods=['POST'])
def scraper_mubawab_endpoint():
    data = request.get_json() or {}
    region = data.get('region', 'rabat')
    max_pages = data.get('max_pages', 3)

    if region not in ('casablanca', 'rabat', 'all'):
        return jsonify({'error': f'Région invalide : {region}'}), 400

    task_id = str(uuid.uuid4())
    create_task(task_id, "Mubawab", f"Démarrage scraping Mubawab ({region})...")
    
    start_scraping_task(
        task_id,
        "Mubawab",
        False, # is_async
        scraper_mubawab_sync,
        region=region,
        max_pages=max_pages,
        headless=True
    )
    
    return jsonify({
        'message': 'Scraping Mubawab lancé en arrière-plan.',
        'task_id': task_id
    })

@app.route('/api/scraper/status/<task_id>', methods=['GET'])
def scraper_status(task_id):
    status = get_task_status(task_id)
    if not status:
        return jsonify({'error': 'Tâche introuvable'}), 404
    return jsonify(status)

# ==================== FAVORIS ====================

@app.route('/api/favoris', methods=['GET'])
def favoris_list():
    try:
        return jsonify(get_favoris())
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/favoris', methods=['POST'])
def favoris_add():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        source = data.get('source')
        annonce_id = data.get('annonce_id')
        if not source or annonce_id is None or annonce_id == '':
            return jsonify({'error': 'source et annonce_id sont requis'}), 400
        
        annonce_id = str(annonce_id)
        app.logger.info(f"Ajout favori : source={source}, annonce_id={annonce_id}")
        
        url = data.get('url', '')
        titre = data.get('titre', 'Sans titre')
        localisation = data.get('localisation', '')
        type_bien = data.get('type_bien', '')
        surface = data.get('surface', '')
        prix = data.get('prix', '')
        prix_m2 = data.get('prix_m2', None)
        
        inserted = ajouter_favori(source, annonce_id, url, titre, localisation, type_bien, surface, prix, prix_m2)
        if inserted:
            return jsonify({'message': 'Annonce ajoutée aux favoris'}), 201
        else:
            return jsonify({'message': 'Annonce déjà dans les favoris'}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/favoris', methods=['DELETE'])
def favoris_delete():
    try:
        data = request.get_json(silent=True) or {}
        source = request.args.get('source') or data.get('source')
        annonce_id = request.args.get('annonce_id') or data.get('annonce_id')
        if not source or annonce_id is None or annonce_id == '':
            return jsonify({'error': 'source et annonce_id sont requis'}), 400
        deleted = supprimer_favori(source, str(annonce_id))
        if deleted:
            return jsonify({'message': 'Annonce retirée des favoris'}), 200
        return jsonify({'message': 'Annonce non trouvée dans les favoris'}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/favoris/<source>/<path:annonce_id>', methods=['DELETE'])
def favoris_delete_legacy(source, annonce_id):
    """Rétrocompatibilité pour les IDs sans slash."""
    try:
        deleted = supprimer_favori(source, annonce_id)
        if deleted:
            return jsonify({'message': 'Annonce retirée des favoris'}), 200
        return jsonify({'message': 'Annonce non trouvée dans les favoris'}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/favoris/set', methods=['GET'])
def favoris_set():
    try:
        from database.db_manager import get_favoris_set
        return jsonify(get_favoris_set())
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/favoris/check/<source>/<annonce_id>', methods=['GET'])
def favoris_check(source, annonce_id):
    try:
        exists = est_favori(source, annonce_id)
        return jsonify({'favori': exists})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)