# api/trends_routes.py
import traceback

from flask import Blueprint, jsonify, request

from services.trends_service import (
    get_evolution_prix_m2,
    get_evolution_nb_annonces,
    get_zones_disponibles,
    get_types_disponibles,
    GRANULARITES,
)

trends_bp = Blueprint('trends', __name__)


def _parse_types(args):
    raw = args.get('types')
    if not raw:
        return None
    return [t.strip() for t in raw.split(',') if t.strip()]


@trends_bp.route('/api/trends/evolution', methods=['GET'])
def trends_evolution():
    try:
        metric = request.args.get('metric', 'prix_m2')
        granularite = request.args.get('granularite', 'run')
        date_from = request.args.get('date_from') or None
        date_to = request.args.get('date_to') or None
        types = _parse_types(request.args)

        if metric == 'nb_annonces':
            data = get_evolution_nb_annonces(
                granularite=granularite, date_from=date_from, date_to=date_to, types=types
            )
        else:
            data = get_evolution_prix_m2(
                granularite=granularite, date_from=date_from, date_to=date_to, types=types
            )
        data['metric'] = 'nb_annonces' if metric == 'nb_annonces' else 'prix_m2'
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@trends_bp.route('/api/trends/meta', methods=['GET'])
def trends_meta():
    try:
        return jsonify({
            'zones': get_zones_disponibles(),
            'types': get_types_disponibles(),
            'granularites': list(GRANULARITES),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
