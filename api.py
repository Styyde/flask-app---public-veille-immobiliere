# api.py
import asyncio
import traceback

from flask import Flask, request, jsonify, render_template

from config import REGIONS
from scraper.runner import scrape_regions
from scraper.sarouty import scraper_sarouty
from scraper.mubawab_scraper_single import scraper_mubawab_sync
from database.db_manager import get_projet_detail, get_statistiques_globales, init_db
from services.filter_service import (
    parse_filtres_from_request,
    filtrer_alomrane,
    filtrer_sarouty,
    filtrer_mubawab,
    get_filtres_disponibles,
    get_prix_m2_moyen_par_groupe,
)
from services.analysis_service import get_analytics_dashboard

app = Flask(__name__)
init_db()


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
            etage=request.args.get('etage'),
        )
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@app.route('/api/filtrer', methods=['GET'])
def filtrer_legacy():
    """Rétrocompatibilité."""
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
            'badge': p['badge'],
        } for p in projets],
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

    try:
        nb = scraper_sarouty(max_pages=max_pages, region_ids=region_ids, category=category)
        return jsonify({'message': 'Scraping Sarouty terminé.', 'nouveaux': nb})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/scraper_mubawab', methods=['POST'])
def scraper_mubawab_endpoint():
    data = request.get_json() or {}
    region = data.get('region', 'rabat')
    max_pages = data.get('max_pages', 3)

    if region not in ('casablanca', 'rabat', 'all'):
        return jsonify({'error': f'Région invalide : {region}'}), 400

    try:
        nb = scraper_mubawab_sync(region=region, max_pages=max_pages, headless=True)
        return jsonify({
            'message': f'Scraping Mubawab terminé ({region}).',
            'nouveaux': nb,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
