# filters.py — shim de rétrocompatibilité pour gui.py et scripts
from services.filter_service import (
    get_filtered_data,
    get_statistiques_globales_wrapper as get_statistiques_globales,
    get_prix_m2_moyen_par_groupe,
)
