function fmt(val, fallback = '—') {
    if (val === null || val === undefined || val === '' || (typeof val === 'number' && isNaN(val))) {
        return fallback;
    }
    return val;
}

function formatPrix(val) {
    if (val === null || val === undefined || val === '') return '—';
    const n = typeof val === 'number' ? val : parseFloat(String(val).replace(/[^\d.]/g, ''));
    if (isNaN(n)) return String(val);
    return n.toLocaleString('fr-FR') + ' DH';
}

function formatSurface(val) {
    if (val === null || val === undefined || val === '') return '—';
    if (typeof val === 'string' && val.includes('m²')) return val;
    const n = typeof val === 'number' ? val : parseFloat(String(val));
    if (isNaN(n)) return String(val);
    return n.toLocaleString('fr-FR') + ' m²';
}

function formatPrixM2(val) {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return Number(val).toLocaleString('fr-FR') + ' DH/m²';
}

function formatPrixM2Range(min, max) {
    if (min == null && max == null) return '—';
    if (min === max) return formatPrixM2(min);
    return `${fmt(min, '?')} – ${fmt(max, '?')} DH/m²`;
}

async function fetchJSON(url) {
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Erreur serveur');
    return data;
}

function buildFilterParams() {
    const params = new URLSearchParams();
    const fields = [
        'source', 'budget_min', 'budget_max', 'ville', 'type_bien',
        'badge', 'etage', 'surface_min', 'surface_max', 'prix_m2_min', 'prix_m2_max',
    ];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value) params.append(id, el.value);
    });
    return params;
}

function badgeHTML(badge) {
    if (!badge) return '—';
    const cls = badge === 'Promotion' ? 'badge-promo' : badge === 'Nouveau' ? 'badge-nouveau' : '';
    return cls ? `<span class="badge ${cls}">${badge}</span>` : fmt(badge);
}

function openUrl(url) {
    if (url) window.open(url, '_blank', 'noopener');
}
