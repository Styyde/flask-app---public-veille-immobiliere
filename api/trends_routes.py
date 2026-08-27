# api/trends_routes.py
import traceback

from flask import Blueprint, jsonify, request

from services.trends_service import (
    get_comparaison_villes,
    get_distribution_types,
    get_types_disponibles,
    get_villes_disponibles,
)

trends_bp = Blueprint('trends', __name__)


def _parse_csv(args, key):
    raw = args.get(key)
    if not raw:
        return None
    return [v.strip() for v in raw.split(',') if v.strip()]


@trends_bp.route('/api/trends/meta', methods=['GET'])
def trends_meta():
    try:
        return jsonify({
            'villes': get_villes_disponibles(),
            'types': get_types_disponibles(),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@trends_bp.route('/api/trends/distribution-types', methods=['GET'])
def trends_distribution_types():
    try:
        date_from = request.args.get('date_from') or None
        date_to = request.args.get('date_to') or None
        return jsonify(get_distribution_types(date_from=date_from, date_to=date_to))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@trends_bp.route('/api/trends/comparaison-villes', methods=['GET'])
def trends_comparaison_villes():
    try:
        villes = _parse_csv(request.args, 'villes')
        type_bien = request.args.get('type') or None
        date_from = request.args.get('date_from') or None
        date_to = request.args.get('date_to') or None
        compare_from = request.args.get('compare_from') or None
        compare_to = request.args.get('compare_to') or None
        return jsonify(get_comparaison_villes(
            villes=villes, type_bien=type_bien,
            date_from=date_from, date_to=date_to,
            compare_from=compare_from, compare_to=compare_to,
        ))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
