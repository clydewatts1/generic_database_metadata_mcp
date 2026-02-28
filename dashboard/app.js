/* ============================================================
   Metadata Graph Dashboard — app.js
   Covers T017 (fetch + canvas), T018 (node click / dim),
   T022 (edge tooltips), T025 (type filter), T026 (search),
   T029-T032 (refresh, truncated, empty state, 503 handler).
   ============================================================ */

/* ---- Storage helpers ---- */
const JWT_KEY = 'dashboard_jwt';

function getStoredToken() {
    return sessionStorage.getItem(JWT_KEY) || localStorage.getItem(JWT_KEY) || '';
}

function storeToken(token) {
    sessionStorage.setItem(JWT_KEY, token);
}

/* ---- Global state ---- */
let cy = null;
let currentPayload = null;    // last successful GraphPayloadResponse
let filterState = {
    selectedTypes: new Set(),  // currently active Object Type filter
    searchTerm: '',             // current search input value
};
const EDGE_TOOLTIP_ID = 'edge-tooltip';

/* ==============================================================
   T017 — Part 1: Initialisation, fetch, and canvas render
   ============================================================== */

document.addEventListener('DOMContentLoaded', () => {
    /* Create edge tooltip element */
    const tooltip = document.createElement('div');
    tooltip.id = EDGE_TOOLTIP_ID;
    tooltip.style.display = 'none';
    document.body.appendChild(tooltip);

    const token = getStoredToken();
    if (!token) {
        showLoginBanner();
    } else {
        loadGraph();
    }

    /* JWT submit button */
    document.getElementById('jwt-submit-btn').addEventListener('click', () => {
        const inputVal = document.getElementById('jwt-input').value.trim();
        if (inputVal) {
            storeToken(inputVal);
            hideAll();
            loadGraph();
        }
    });

    /* Refresh button — T029 */
    document.getElementById('refresh-btn').addEventListener('click', () => {
        clearFilterState();
        loadGraph();
    });

    /* Keyboard: Escape clears selection / search */
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            clearNodeSelection();
        }
    });

    /* Detail-panel close button */
    document.getElementById('detail-close-btn').addEventListener('click', clearNodeSelection);

    /* Type filter change — T025 */
    document.getElementById('type-filter').addEventListener('change', () => {
        const select = document.getElementById('type-filter');
        filterState.selectedTypes = new Set(
            Array.from(select.selectedOptions).map(o => o.value)
        );
        applyFilters();
    });

    /* Clear filter — T025 */
    document.getElementById('clear-filter-btn').addEventListener('click', () => {
        const select = document.getElementById('type-filter');
        Array.from(select.options).forEach(o => { o.selected = false; });
        filterState.selectedTypes.clear();
        applyFilters();
    });

    /* Search input — T026 (debounced) */
    const searchInput = document.getElementById('search-input');
    let searchTimer = null;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            filterState.searchTerm = searchInput.value.trim();
            applySearch();
        }, 200);
    });
});

/* ---- Fetch & render ----- */

async function loadGraph() {
    const token = getStoredToken();
    if (!token) {
        showLoginBanner();
        return;
    }

    showSpinner(true);
    hideElement('error-banner');
    hideElement('truncated-banner');
    hideElement('empty-state-global');

    try {
        const response = await fetch('/api/graph', {
            headers: { 'Authorization': `Bearer ${token}` },
        });

        if (response.status === 401) {
            showLoginBanner();
            showSpinner(false);
            return;
        }

        if (response.status === 403) {
            showElement('scope-error-banner');
            showSpinner(false);
            return;
        }

        if (response.status === 503) {
            /* T032: preserve last rendered state, show error banner */
            showElement('error-banner');
            showSpinner(false);
            return;   // Do NOT blank the canvas
        }

        if (!response.ok) {
            showElement('error-banner');
            showSpinner(false);
            return;
        }

        const payload = await response.json();
        currentPayload = payload;

        /* T030: Truncated banner */
        if (payload.truncated) {
            showElement('truncated-banner');
        }

        /* T031: Empty graph state */
        if (payload.node_count === 0) {
            showSpinner(false);
            showElement('empty-state-global');
            hideElement('cy');
            return;
        }

        showElement('cy');
        document.getElementById('scope-badge').textContent = `Scope: ${payload.scope}`;
        populateTypeFilter(payload.meta_types);
        renderGraph(payload);

    } catch (err) {
        console.error('Dashboard fetch error:', err);
        /* T032: show error banner, preserve canvas */
        showElement('error-banner');
        showSpinner(false);
    }
}

function renderGraph(payload) {
    /* Build Cytoscape element array */
    const elements = [];

    /* Nodes */
    for (const node of payload.nodes) {
        const hasBusiness = node.business_name && node.business_name.trim();
        /* FR-014: business_name primary + label smaller secondary text */
        /* Cytoscape.js doesn't support mixed font sizes natively; compose as two lines */
        const composedLabel = hasBusiness
            ? `${node.business_name}\n${node.label}`
            : node.label;

        elements.push({
            group: 'nodes',
            data: {
                id: node.id,
                label: node.label,                     // technical label
                business_name: node.business_name,     // human-readable alias (or null)
                primary_label: composedLabel,          // FR-014 composed display
                meta_type_name: node.meta_type_name,
                domain_scope: node.domain_scope,
                properties: node.properties,
            },
        });
    }

    /* Edges */
    for (const edge of payload.edges) {
        elements.push({
            group: 'edges',
            data: {
                id: edge.id,
                source: edge.source_id,
                target: edge.target_id,
                edge_type: edge.edge_type,
                is_stigmergic: edge.is_stigmergic,
                confidence_score: edge.confidence_score ?? 0,
                rationale_summary: edge.rationale_summary,
                last_accessed: edge.last_accessed,
            },
        });
    }

    /* Destroy previous instance */
    if (cy) {
        cy.destroy();
        cy = null;
    }

    cy = cytoscape({
        container: document.getElementById('cy'),
        elements,
        style: buildCytoscapeStyle(),
        layout: { name: 'cose', animate: false, randomize: true, numIter: 500 },
        minZoom: 0.05,
        maxZoom: 10,
    });

    /* FR-005: zoom/pan enabled by default in Cytoscape.js */

    /* Register interaction handlers */
    registerNodeClickHandler();
    registerEdgeTooltipHandler();  /* T022 */

    showSpinner(false);
}

/* ---- Cytoscape style --------------------------------------------------------
   FR-004: stigmergic edge width = confidence_score * 5 + 1 (1px–6px linear)
           mapData(confidence_score, 0, 1, 1, 6) achieves exactly this.
   FR-013: confidence < 0.2 → dashed, opacity 0.4 (de-emphasised)
   Structural edges → 1.5px solid grey
   FR-014: business_name primary label; label text as secondary
   --------------------------------------------------------------------------- */
function buildCytoscapeStyle() {
    return [
        /* === NODES === */
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'font-size': 11,
                'background-color': '#3b82f6',
                'border-color': '#1d4ed8',
                'border-width': 1,
                'color': '#e2e8f0',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'text-margin-y': 4,
                'width': 30,
                'height': 30,
                'text-max-width': 120,
                'text-wrap': 'ellipsis',
                'text-overflow-wrap': 'whitespace',
            },
        },
        /* FR-014: nodes with business_name show composed two-line label */
        {
            selector: 'node[?business_name]',
            style: {
                'label': 'data(primary_label)',
                'text-wrap': 'wrap',
                'font-size': 11,
            },
        },
        /* Dimmed class (1-hop highlight, search) */
        {
            selector: 'node.dimmed',
            style: {
                'opacity': 0.15,
            },
        },

        /* === STIGMERGIC EDGES (is_stigmergic = true) ===
           FR-004: width = confidence_score * 5 + 1  (mapData: [0,1] → [1,6]) */
        {
            selector: 'edge[?is_stigmergic]',
            style: {
                'width': 'mapData(confidence_score, 0, 1, 1, 6)',
                'line-color': 'mapData(confidence_score, 0, 1, #6366f1, #a855f7)',
                'line-style': 'solid',
                'opacity': 1,
                'curve-style': 'bezier',
                'target-arrow-shape': 'none',
            },
        },
        /* FR-013: low-confidence stigmergic → dashed, de-emphasised */
        {
            selector: 'edge[?is_stigmergic][confidence_score < 0.2]',
            style: {
                'line-style': 'dashed',
                'opacity': 0.4,
                'line-dash-pattern': [6, 4],
            },
        },

        /* === STRUCTURAL / FLOW EDGES (is_stigmergic = false) === */
        {
            selector: 'edge[!is_stigmergic]',
            style: {
                'width': 1.5,
                'line-color': '#475569',
                'line-style': 'solid',
                'opacity': 0.8,
                'curve-style': 'bezier',
                'target-arrow-shape': 'none',
            },
        },

        /* Dimmed edges */
        {
            selector: 'edge.dimmed',
            style: { 'opacity': 0.08 },
        },
    ];
}

/* ==============================================================
   T018 — Part 2: Node click → side panel + 1-hop dim
   ============================================================== */

function registerNodeClickHandler() {
    cy.on('tap', 'node', (event) => {
        const tapped = event.target;
        openDetailPanel(tapped);

        /* 1-hop dim: dim all nodes/edges not connected to tapped */
        const neighbourhood = tapped.closedNeighborhood();  // node + direct neighbours
        cy.elements().not(neighbourhood).addClass('dimmed');
        neighbourhood.removeClass('dimmed');
    });

    /* Background click → clear dim + close panel */
    cy.on('tap', (event) => {
        if (event.target === cy) {
            clearNodeSelection();
        }
    });
}

function openDetailPanel(node) {
    const panel = document.getElementById('detail-panel');
    document.getElementById('detail-title').textContent =
        node.data('business_name') || node.data('label');

    const dl = document.getElementById('detail-props');
    dl.innerHTML = '';

    /* Fixed fields */
    _addProp(dl, 'Object Type', node.data('meta_type_name'));
    _addProp(dl, 'Domain Scope', node.data('domain_scope'));
    _addProp(dl, 'Technical Label', node.data('label'));

    /* Dynamic properties from the node's properties dict */
    const props = node.data('properties');
    if (props && typeof props === 'object') {
        for (const [k, v] of Object.entries(props)) {
            if (k !== 'label' && k !== 'business_name') {
                _addProp(dl, k, String(v));
            }
        }
    }

    panel.classList.remove('hidden');
}

function _addProp(dl, key, value) {
    const dt = document.createElement('dt');
    dt.textContent = key;
    const dd = document.createElement('dd');
    dd.textContent = value !== null && value !== undefined ? value : '—';
    dl.appendChild(dt);
    dl.appendChild(dd);
}

function clearNodeSelection() {
    if (!cy) return;
    cy.elements().removeClass('dimmed');
    document.getElementById('detail-panel').classList.add('hidden');
    /* Restore any active filter/search dim */
    applyFilters();
    applySearch();
}

/* ==============================================================
   T022 (Phase 5) — Part 3: Edge tooltips
   ============================================================== */

function registerEdgeTooltipHandler() {
    if (!cy) return;
    const tooltip = document.getElementById(EDGE_TOOLTIP_ID);

    cy.on('mouseover', 'edge', (e) => {
        const edge = e.target;
        const data = edge.data();
        let html = '';

        if (data.is_stigmergic) {
            /* Stigmergic tooltip: type, confidence, rationale, last_accessed */
            html = [
                `<strong>Type:</strong> ${data.edge_type}`,
                `<strong>Confidence:</strong> ${(data.confidence_score ?? 0).toFixed(2)}`,
                data.rationale_summary
                    ? `<strong>Rationale:</strong> ${data.rationale_summary}`
                    : '',
                data.last_accessed
                    ? `<strong>Last accessed:</strong> ${data.last_accessed}`
                    : '',
            ].filter(Boolean).join('<br>');
        } else {
            /* Structural tooltip: type + source/target names */
            const srcNode = cy.getElementById(data.source);
            const tgtNode = cy.getElementById(data.target);
            const srcName = srcNode.data('business_name') || srcNode.data('label') || data.source;
            const tgtName = tgtNode.data('business_name') || tgtNode.data('label') || data.target;
            html = [
                `<strong>Type:</strong> ${data.edge_type}`,
                `<strong>From:</strong> ${srcName}`,
                `<strong>To:</strong> ${tgtName}`,
            ].join('<br>');
        }

        tooltip.innerHTML = html;
        tooltip.style.display = 'block';
        positionTooltip(tooltip, e.originalEvent);
    });

    cy.on('mousemove', 'edge', (e) => {
        positionTooltip(tooltip, e.originalEvent);
    });

    cy.on('mouseout', 'edge', () => {
        tooltip.style.display = 'none';
    });
}

function positionTooltip(tooltip, mouseEvent) {
    if (!mouseEvent) return;
    const x = mouseEvent.clientX + 14;
    const y = mouseEvent.clientY + 14;
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
}

/* ==============================================================
   T025 (Phase 6) — Part 4: Object Type filter
   ============================================================== */

function populateTypeFilter(metaTypes) {
    const select = document.getElementById('type-filter');
    select.innerHTML = '';
    for (const t of metaTypes) {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        select.appendChild(opt);
    }
}

function applyFilters() {
    if (!cy) return;
    const { selectedTypes } = filterState;

    if (selectedTypes.size === 0) {
        /* No filter — restore all */
        cy.nodes().style('display', 'element');
        cy.edges().style('display', 'element');
        hideElement('empty-state');
        return;
    }

    let visibleCount = 0;
    /* Hide/show nodes by meta_type_name */
    cy.nodes().forEach((node) => {
        const visible = selectedTypes.has(node.data('meta_type_name'));
        node.style('display', visible ? 'element' : 'none');
        if (visible) visibleCount++;
    });

    /* Hide edges whose source or target is hidden */
    cy.edges().forEach((edge) => {
        const src = cy.getElementById(edge.data('source'));
        const tgt = cy.getElementById(edge.data('target'));
        const srcVisible = src.style('display') !== 'none';
        const tgtVisible = tgt.style('display') !== 'none';
        edge.style('display', (srcVisible && tgtVisible) ? 'element' : 'none');
    });

    /* T025: zero-match empty-state message */
    if (visibleCount === 0) {
        showElement('empty-state');
    } else {
        hideElement('empty-state');
    }
}

/* ==============================================================
   T026 (Phase 6) — Part 5: business_name search with re-centering
   ============================================================== */

const MAX_SEARCH_MATCHES = 50;

function applySearch() {
    if (!cy) return;
    const term = filterState.searchTerm.toLowerCase();

    /* Clear dim on empty term */
    if (!term) {
        cy.elements().removeClass('dimmed');
        hideElement('match-count');
        applyFilters();
        return;
    }

    /* Find matching nodes: only nodes with business_name set, case-insensitive contains */
    const matching = cy.nodes().filter((node) => {
        const bn = node.data('business_name');
        return bn && bn.toLowerCase().includes(term);
    });

    /* Dim non-matching nodes */
    cy.nodes().forEach((node) => {
        if (matching.has(node)) node.removeClass('dimmed');
        else node.addClass('dimmed');
    });

    /* Dim edges that don't connect to any matching node */
    cy.edges().forEach((edge) => {
        const src = cy.getElementById(edge.data('source'));
        const tgt = cy.getElementById(edge.data('target'));
        const connected = matching.has(src) || matching.has(tgt);
        if (connected) edge.removeClass('dimmed');
        else edge.addClass('dimmed');
    });

    /* T026: Re-centre on best match = matching node with highest direct edge count */
    if (matching.length > 0) {
        let bestMatchNode = matching[0];
        let bestEdgeCount = bestMatchNode.connectedEdges().length;
        matching.forEach((n) => {
            const cnt = n.connectedEdges().length;
            if (cnt > bestEdgeCount) {
                bestEdgeCount = cnt;
                bestMatchNode = n;
            }
        });
        cy.animate({ center: { eles: bestMatchNode }, duration: 300 });
    }

    /* T026: match-count notice; cap at 50 */
    const matchCountEl = document.getElementById('match-count');
    if (matching.length === 0) {
        matchCountEl.textContent = 'No matches';
        matchCountEl.style.display = 'inline';
    } else if (matching.length > MAX_SEARCH_MATCHES) {
        matchCountEl.textContent = `Showing first ${MAX_SEARCH_MATCHES} of ${matching.length} matches`;
        matchCountEl.style.display = 'inline';
    } else {
        matchCountEl.textContent = `${matching.length} match${matching.length === 1 ? '' : 'es'}`;
        matchCountEl.style.display = 'inline';
    }
}

/* ==============================================================
   Phase 7 helpers (T029-T032 Polish)
   ============================================================== */

function clearFilterState() {
    /* T029: reset all filter state on refresh */
    filterState.selectedTypes.clear();
    filterState.searchTerm = '';
    const select = document.getElementById('type-filter');
    if (select) Array.from(select.options).forEach(o => { o.selected = false; });
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = '';
    hideElement('match-count');
}

/* ==============================================================
   DOM helpers
   ============================================================== */

function showLoginBanner() {
    document.getElementById('login-banner').classList.remove('hidden');
}

function hideAll() {
    ['login-banner', 'scope-error-banner', 'error-banner', 'truncated-banner'].forEach(hideElement);
}

function showElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
}

function hideElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

function showSpinner(visible) {
    const el = document.getElementById('loading-spinner');
    if (!el) return;
    if (visible) el.classList.remove('hidden');
    else el.classList.add('hidden');
}

