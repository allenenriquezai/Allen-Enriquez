/* EPS Dashboard — Kanban UI (Light Mode) */

let activeTab = 'overview';
let currentPipeline = '';
let currentBoard = '';

// --- Auth ---

function checkAuth() {
    const token = localStorage.getItem('eps_dashboard_token');
    if (!token) {
        document.getElementById('page-login').classList.remove('hidden');
        document.getElementById('app-shell').classList.add('hidden');
        return false;
    }
    document.getElementById('page-login').classList.add('hidden');
    document.getElementById('app-shell').classList.remove('hidden');
    return true;
}

async function doLogin() {
    const input = document.getElementById('login-input');
    const error = document.getElementById('login-error');
    const token = input.value.trim();
    if (!token) return;
    try {
        const res = await fetch('/api/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Token': token },
            body: JSON.stringify({ token }),
        });
        const data = await res.json();
        if (data.ok) {
            localStorage.setItem('eps_dashboard_token', token);
            error.classList.add('hidden');
            checkAuth();
            loadTab('overview');
        } else {
            error.classList.remove('hidden');
        }
    } catch { error.classList.remove('hidden'); }
}

document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && document.activeElement?.id === 'login-input') doLogin();
});

// --- Tabs ---

function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`page-${tab}`).classList.remove('hidden');
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
    loadTab(tab);
}

function loadTab(tab) {
    if (tab === 'overview') loadOverview();
    else if (tab === 'deals') loadDeals();
    else if (tab === 'tenders') loadTenders();
    else if (tab === 'projects') loadProjects();
    else if (tab === 'reengage') loadReengage();
    else if (tab === 'winback') loadWinBack();
    else if (tab === 'e1inbox') loadE1Inbox();
}

// --- Refresh ---

async function refreshData() {
    const btn = document.getElementById('refresh-btn');
    btn.innerHTML = '<span class="spin">&#8635;</span>';
    btn.disabled = true;
    try { await fetch('/api/refresh', { method: 'POST' }); loadTab(activeTab); }
    finally { btn.innerHTML = 'Refresh'; btn.disabled = false; }
}

async function refreshAnalysis() {
    const btn = document.getElementById('analysis-btn');
    btn.innerHTML = '<span class="spin">&#8635;</span> Running...';
    btn.disabled = true;
    try {
        await fetch('/api/refresh-analysis', { method: 'POST' });
        btn.innerHTML = '~60s...';
        setTimeout(() => { btn.innerHTML = 'Re-analyze'; btn.disabled = false; refreshData(); }, 65000);
    } catch { btn.innerHTML = 'Re-analyze'; btn.disabled = false; }
}

// --- Helpers ---

function fmtVal(val) { return '$' + (val || 0).toLocaleString('en-AU'); }

function daysText(d) {
    if (d === undefined || d === null) return '';
    if (d === 0) return 'today';
    return d + 'd';
}

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

function fmtDateTime(dateStr) {
    if (!dateStr || dateStr.length < 10) return '';
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const y = dateStr.slice(0,4);
    const m = parseInt(dateStr.slice(5,7), 10);
    const d = parseInt(dateStr.slice(8,10), 10);
    const monthName = months[m - 1] || '';
    let result = `${d} ${monthName} ${y}`;
    if (dateStr.length >= 16) {
        let h = parseInt(dateStr.slice(11,13), 10);
        const min = dateStr.slice(14,16);
        const ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12 || 12;
        result += ` ${h}:${min}${ampm}`;
    }
    return result;
}

function fmtDateShort(dateStr) {
    if (!dateStr || dateStr.length < 10) return '';
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const m = parseInt(dateStr.slice(5,7), 10);
    const d = parseInt(dateStr.slice(8,10), 10);
    return `${d} ${months[m - 1] || ''}`;
}

function flagDots(flags) {
    if (!flags?.length) return '';
    const hasOverdue = flags.some(f => f.includes('OVERDUE'));
    return `<span class="inline-block w-2 h-2 rounded-full ${hasOverdue ? 'bg-red-500' : 'bg-amber-500'}" title="${esc(flags.join(', '))}"></span>`;
}

function stageColor(stage) {
    const c = {
        'NEW': 'blue', 'SITE VISIT': 'purple', 'QUOTE IN PROGRESS': 'amber',
        'QUOTE SENT': 'cyan', 'FOLLOW UP': 'yellow', 'CONTACT MADE': 'teal',
        'NEGOTIATION / FOLLOW UP': 'orange', 'LATE FOLLOW UP': 'red', 'DEPOSIT PROCESS': 'green',
        'CONTACTED': 'cyan', 'RESPONDED': 'purple', 'REFERRAL GIVEN': 'green',
        'REPEAT QUOTE': 'amber', 'GOOGLE REVIEW': 'teal', 'DONE': 'gray',
        'QUALIFIED': 'green', 'NOT WORTH IT': 'red', 'INTERESTED': 'green',
    };
    return c[stage] || 'gray';
}

const sm8StatusLabel = {
    'quote': 'Quote', 'work order': 'Work Order', 'Quote': 'Quote',
    'Work Order': 'Work Order', 'in progress': 'In Progress',
    'completed': 'Completed', 'unsuccessful': 'Unsuccessful',
};

function sm8Badge(status) {
    if (!status) return '';
    const colors = {
        'completed': 'bg-green-100 text-green-700',
        'work order': 'bg-blue-100 text-blue-700',
        'in progress': 'bg-blue-100 text-blue-700',
        'quote': 'bg-gray-100 text-gray-600',
        'unsuccessful': 'bg-red-100 text-red-600',
    };
    const cls = colors[status] || 'bg-gray-100 text-gray-600';
    return `<span class="text-[11px] px-2 py-0.5 rounded-full font-medium ${cls}">${esc(sm8StatusLabel[status] || status)}</span>`;
}

// --- Kanban builder ---

function buildKanban(container, columns) {
    container.innerHTML = columns.map(col => `
        <div class="kanban-col">
            <div class="kanban-col-header bg-surface-2 border border-gray-200 flex items-center justify-between">
                <span class="text-sm font-semibold text-${col.color}-600">${esc(col.name)}</span>
                <span class="text-xs text-gray-400">${col.count}</span>
            </div>
            <div class="kanban-col-body space-y-2 mt-1">
                ${col.cards.join('')}
            </div>
        </div>
    `).join('');
}

function dealCard(d) {
    const overdue = d.flags?.some(f => f.includes('OVERDUE'));
    const border = overdue ? 'border-red-300' : 'border-gray-200';
    return `
    <div class="kanban-card bg-surface-2 border ${border} rounded-lg p-3 cursor-pointer" onclick="openDealDetail(${d.deal_id}, event)">
        <div class="flex items-start justify-between gap-1">
            <p class="text-sm font-medium text-gray-900 leading-tight">${esc(d.title)}</p>
            ${flagDots(d.flags)}
        </div>
        ${d.org ? `<p class="text-xs text-gray-500 mt-0.5 truncate">${esc(d.org)}</p>` : ''}
        <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-500">${fmtVal(d.value)}</span>
            <div class="flex items-center gap-1.5">
                ${sm8Badge(d.sm8_status)}
                <span class="text-xs ${d.days_since_activity > 5 ? 'text-red-500 font-medium' : 'text-gray-400'}">${daysText(d.days_since_activity)}</span>
            </div>
        </div>
    </div>`;
}

function projectCard(p) {
    const hasFlags = p.flags?.length;
    const border = hasFlags ? 'border-amber-300' : 'border-gray-200';
    return `
    <div class="kanban-card bg-surface-2 border ${border} rounded-lg p-3 cursor-pointer" onclick="openProjectDetail(${p.project_id}, event)">
        <div class="flex items-start justify-between gap-1">
            <p class="text-sm font-medium text-gray-900 leading-tight">${esc(p.title)}</p>
            ${flagDots(p.flags)}
        </div>
        <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-500">${esc(p.board)}</span>
            <span class="text-xs ${p.days_since_update > 7 ? 'text-amber-600 font-medium' : 'text-gray-400'}">${daysText(p.days_since_update)}</span>
        </div>
    </div>`;
}

function tenderCard(t) {
    const hasDue = t.quotes_due;
    return `
    <div class="kanban-card bg-surface-2 border border-gray-200 rounded-lg p-3">
        <p class="text-sm font-medium text-gray-900 leading-tight">${esc(t.project)}</p>
        <p class="text-xs text-gray-500 mt-0.5 truncate">${esc(t.builder)}</p>
        <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-500">${esc(t.budget || '')}</span>
            <span class="text-xs text-gray-400">${esc(t.distance || '')}</span>
        </div>
        ${hasDue ? `<p class="text-xs text-cyan-600 mt-1">Due: ${esc(t.quotes_due)}</p>` : ''}
        ${t.flags?.length ? `<div class="mt-1">${t.flags.map(f => `<span class="flag-badge bg-amber-100 text-amber-700">${esc(f)}</span>`).join(' ')}</div>` : ''}
    </div>`;
}

// --- Overview ---

async function loadOverview() {
    const res = await fetch('/api/overview');
    const data = await res.json();
    if (!data.ok) return;
    const s = data.stats;

    document.getElementById('last-fetch').textContent = data.last_fetch ? `Live: ${data.last_fetch}` : '';

    document.getElementById('stats-row').innerHTML = `
        <div class="bg-surface-2 border border-gray-200 rounded-xl p-4 text-center">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Deals</div>
            <div class="text-2xl font-bold text-gray-900">${s.active_deals}</div>
            <div class="text-xs text-gray-500 mt-1">${fmtVal(s.total_value)}</div>
        </div>
        <div class="bg-surface-2 border border-gray-200 rounded-xl p-4 text-center">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Quotes Out</div>
            <div class="text-2xl font-bold text-cyan-600">${s.quotes_pending}</div>
        </div>
        <div class="bg-surface-2 border border-gray-200 rounded-xl p-4 text-center">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Tenders</div>
            <div class="text-2xl font-bold text-purple-600">${s.tenders_open}</div>
        </div>
        <div class="bg-surface-2 border border-gray-200 rounded-xl p-4 text-center">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Projects</div>
            <div class="text-2xl font-bold text-blue-600">${s.projects_active}</div>
        </div>
        <div class="bg-surface-2 border ${s.flagged > 0 ? 'border-red-300' : 'border-gray-200'} rounded-xl p-4 text-center">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Flagged</div>
            <div class="text-2xl font-bold ${s.flagged > 0 ? 'text-red-500' : 'text-green-600'}">${s.flagged}</div>
        </div>
    `;

    const alerts = document.getElementById('overview-alerts');
    let html = '';

    if (data.questions.length) {
        html += `<h3 class="text-sm font-semibold text-amber-600 uppercase tracking-wider mt-2 mb-2">Questions (${data.questions.length})</h3>`;
        html += data.questions.slice(0, 8).map(q => `
            <div class="bg-surface-2 border border-amber-200 rounded-lg px-3 py-2 flex items-start gap-3">
                <span class="text-xs font-medium text-amber-600 uppercase w-10 shrink-0 pt-0.5">${esc((q.priority || '').toUpperCase())}</span>
                <div class="min-w-0">
                    <span class="text-sm text-gray-900">${esc(q.title)}</span>
                    <span class="text-xs text-gray-500 ml-1">${esc(q.question)}</span>
                </div>
            </div>
        `).join('');
    }

    if (data.attention.length) {
        html += `<h3 class="text-sm font-semibold text-red-500 uppercase tracking-wider mt-4 mb-2">Needs Attention (${data.attention.length})</h3>`;
        html += data.attention.slice(0, 10).map(a => `
            <div class="bg-surface-2 border border-gray-200 rounded-lg px-3 py-2 flex items-center justify-between">
                <div class="flex items-center gap-2 min-w-0">
                    ${flagDots(a.flags)}
                    <span class="text-sm text-gray-900 truncate">${esc(a.title)}</span>
                    <span class="text-xs text-gray-500">${esc(a.pipeline || a.board)}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <span class="stage-pill bg-${stageColor(a.stage || a.phase)}-100 text-${stageColor(a.stage || a.phase)}-700">${esc(a.stage || a.phase)}</span>
                    <span class="text-xs text-gray-400">${daysText(a.days_since_activity || a.days_since_update)}</span>
                </div>
            </div>
        `).join('');
    }

    if (!data.questions.length && !data.attention.length) {
        html = '<p class="text-sm text-gray-400 py-8 text-center">All clear</p>';
    }

    alerts.innerHTML = html;
}

// --- Deals Kanban (split by pipeline) ---

const DEAL_STAGE_ORDER = [
    'NEW', 'SITE VISIT', 'QUOTE IN PROGRESS', 'QUOTE SENT',
    'NEGOTIATION / FOLLOW UP', 'LATE FOLLOW UP', 'DEPOSIT PROCESS'
];

const TENDER_STAGE_ORDER = [
    'QUOTE IN PROGRESS', 'QUOTE SENT', 'FOLLOW UP',
    'CONTACT MADE', 'NEGOTIATION / FOLLOW UP', 'LATE FOLLOW UP'
];

function buildPipelineKanban(deals, containerId, countId) {
    const groups = {};
    deals.forEach(d => {
        const s = d.stage || 'UNKNOWN';
        if (!groups[s]) groups[s] = [];
        groups[s].push(d);
    });

    const columns = DEAL_STAGE_ORDER
        .map(s => ({
            name: s, color: stageColor(s), count: (groups[s] || []).length,
            cards: (groups[s] || []).map(d => dealCard(d)),
        }));

    const el = document.getElementById(countId);
    if (el) el.textContent = `${deals.length} deals`;

    const container = document.getElementById(containerId);
    if (!columns.length) { container.innerHTML = '<p class="text-xs text-gray-400 py-2">No deals</p>'; return; }
    buildKanban(container, columns);
}

async function loadDeals() {
    const res = await fetch('/api/deals?sort=days_since_activity&dir=desc');
    const data = await res.json();
    if (!data.ok) return;

    document.getElementById('last-fetch').textContent = data.last_fetch ? `Live: ${data.last_fetch}` : '';

    const byPipeline = { 'EPS Clean': [], 'EPS Paint': [] };
    data.deals.forEach(d => { if (byPipeline[d.pipeline]) byPipeline[d.pipeline].push(d); });

    buildPipelineKanban(byPipeline['EPS Clean'], 'deals-clean-kanban', 'deals-clean-count');
    buildPipelineKanban(byPipeline['EPS Paint'], 'deals-paint-kanban', 'deals-paint-count');
}

// --- Sent Tenders ---

async function loadTenders() {
    const res = await fetch('/api/deals?sort=days_since_activity&dir=desc');
    const data = await res.json();
    if (!data.ok) return;

    const byPipeline = { 'Tenders - Clean': [], 'Tenders - Paint': [] };
    data.deals.forEach(d => { if (byPipeline[d.pipeline]) byPipeline[d.pipeline].push(d); });

    buildPipelineKanban(byPipeline['Tenders - Clean'], 'tenders-clean-kanban', 'tenders-clean-count');
    buildPipelineKanban(byPipeline['Tenders - Paint'], 'tenders-paint-kanban', 'tenders-paint-count');
}

// --- E1 Inbox ---

async function loadE1Inbox() {
    const res = await fetch('/api/tenders');
    const data = await res.json();
    if (!data.ok) return;

    document.getElementById('e1-scraped').textContent = data.scraped_at ? `Scraped: ${data.scraped_at}` : '';

    const leadGroups = {};
    data.leads.forEach(t => {
        const pkg = t.package || t.category || 'Other';
        if (!leadGroups[pkg]) leadGroups[pkg] = [];
        leadGroups[pkg].push(t);
    });
    const leadCols = Object.keys(leadGroups).sort().map(pkg => ({
        name: pkg, color: 'cyan', count: leadGroups[pkg].length,
        cards: leadGroups[pkg].map(t => tenderCard(t)),
    }));
    if (!leadCols.length) leadCols.push({ name: 'No Leads', color: 'gray', count: 0, cards: ['<p class="text-xs text-gray-400 py-2">None</p>'] });
    buildKanban(document.getElementById('e1-leads-kanban'), leadCols);

    const catGroups = {};
    data.open_tenders.forEach(t => {
        const cat = t.category || 'Other';
        if (!catGroups[cat]) catGroups[cat] = [];
        catGroups[cat].push(t);
    });
    const openCols = Object.keys(catGroups).sort().map(cat => ({
        name: cat, color: 'purple', count: catGroups[cat].length,
        cards: catGroups[cat].map(t => tenderCard(t)),
    }));
    buildKanban(document.getElementById('e1-open-kanban'), openCols);
}

// --- Projects Kanban ---

const CLEAN_PROJECT_PHASES = [
    'Recurring Active', 'New', 'Pending Booking', 'Booked', 'Fixups',
    'Completed', 'Variations', 'Final Invoice', 'Forward to Google Review'
];
const PAINT_PROJECT_PHASES = [
    'New', 'Pending Booking', 'Booked', 'Fix Ups',
    'Completed', 'Variations', 'Final Invoice'
];
const PROJECT_PHASE_ORDER = [...new Set([...CLEAN_PROJECT_PHASES, ...PAINT_PROJECT_PHASES])];

function buildProjectKanbanWithPhases(projects, phaseOrder, containerId, countId) {
    const groups = {};
    projects.forEach(p => {
        const ph = p.phase || 'Unknown';
        if (!groups[ph]) groups[ph] = [];
        groups[ph].push(p);
    });

    const columns = phaseOrder.map(ph => ({
        name: ph, color: 'blue', count: (groups[ph] || []).length,
        cards: (groups[ph] || []).map(p => projectCard(p)),
    }));

    Object.keys(groups).forEach(ph => {
        if (!phaseOrder.includes(ph)) {
            columns.push({ name: ph, color: 'gray', count: groups[ph].length, cards: groups[ph].map(p => projectCard(p)) });
        }
    });

    const el = document.getElementById(countId);
    if (el) el.textContent = `${projects.length} projects`;

    const container = document.getElementById(containerId);
    buildKanban(container, columns);
}

function buildProjectKanban(projects, containerId, countId) {
    const groups = {};
    projects.forEach(p => {
        const ph = p.phase || 'Unknown';
        if (!groups[ph]) groups[ph] = [];
        groups[ph].push(p);
    });

    const columns = PROJECT_PHASE_ORDER
        .map(ph => ({
            name: ph, color: 'blue', count: (groups[ph] || []).length,
            cards: (groups[ph] || []).map(p => projectCard(p)),
        }));

    Object.keys(groups).forEach(ph => {
        if (!PROJECT_PHASE_ORDER.includes(ph)) {
            columns.push({ name: ph, color: 'gray', count: groups[ph].length, cards: groups[ph].map(p => projectCard(p)) });
        }
    });

    const el = document.getElementById(countId);
    if (el) el.textContent = `${projects.length} projects`;

    const container = document.getElementById(containerId);
    if (!columns.length) { container.innerHTML = '<p class="text-xs text-gray-400 py-2">No projects</p>'; return; }
    buildKanban(container, columns);
}

async function loadProjects() {
    const res = await fetch('/api/projects');
    const data = await res.json();
    if (!data.ok) return;

    const clean = data.projects.filter(p => p.board === 'EPS Clean Projects');
    const paint = data.projects.filter(p => p.board === 'EPS Paint Projects');

    buildProjectKanbanWithPhases(clean, CLEAN_PROJECT_PHASES, 'proj-clean-kanban', 'proj-clean-count');
    buildProjectKanbanWithPhases(paint, PAINT_PROJECT_PHASES, 'proj-paint-kanban', 'proj-paint-count');
}

const REENGAGE_STAGE_ORDER = [
    'NEW', 'CONTACTED', 'RESPONDED', 'REFERRAL GIVEN',
    'REPEAT QUOTE', 'GOOGLE REVIEW', 'DONE'
];

async function loadReengage() {
    const res = await fetch('/api/deals?sort=days_since_activity&dir=desc');
    const data = await res.json();
    if (!data.ok) return;

    const deals = data.deals.filter(d => d.pipeline === 'Re-engagement');
    const el = document.getElementById('reengage-count');
    if (el) el.textContent = `${deals.length} contacts`;

    buildPipelineKanban(deals, 'reengage-kanban', null);
}

const WINBACK_STAGE_ORDER = ['NEW', 'QUALIFIED', 'NOT WORTH IT', 'CONTACTED', 'INTERESTED'];

async function loadWinBack() {
    const res = await fetch('/api/deals?sort=days_since_activity&dir=desc');
    const data = await res.json();
    if (!data.ok) return;

    const deals = data.deals.filter(d => d.pipeline === 'Win-Back');
    const el = document.getElementById('winback-count');
    if (el) el.textContent = `${deals.length} contacts`;

    buildPipelineKanban(deals, 'winback-kanban', null);
}

// Override stage order for re-engagement/win-back/tenders
const _origBuildPipelineKanban = buildPipelineKanban;
buildPipelineKanban = function(deals, containerId, countId) {
    const groups = {};
    deals.forEach(d => {
        const s = d.stage || 'UNKNOWN';
        if (!groups[s]) groups[s] = [];
        groups[s].push(d);
    });

    const pipeline = deals.length > 0 ? deals[0].pipeline : '';
    const order = pipeline === 'Re-engagement' ? REENGAGE_STAGE_ORDER
                : pipeline === 'Win-Back' ? WINBACK_STAGE_ORDER
                : (pipeline === 'Tenders - Clean' || pipeline === 'Tenders - Paint') ? TENDER_STAGE_ORDER
                : DEAL_STAGE_ORDER;

    const columns = order
        .map(s => ({
            name: s, color: stageColor(s), count: (groups[s] || []).length,
            cards: (groups[s] || []).map(d => dealCard(d)),
        }));

    if (countId) {
        const el = document.getElementById(countId);
        if (el) el.textContent = `${deals.length} deals`;
    }

    const container = document.getElementById(containerId);
    if (!columns.length) { container.innerHTML = '<p class="text-xs text-gray-400 py-2">No deals</p>'; return; }
    buildKanban(container, columns);
};

// --- SM8 Activity Timeline (shared between deal + project modals) ---

function renderActivities(activities) {
    if (!activities || !activities.length) return '';
    let html = `<div class="modal-section"><h3>SM8 Activity (${activities.length})</h3>`;
    activities.forEach(a => {
        // Parse [Type] prefix from note if present
        let actType = a.is_site_visit ? 'Booking' : 'Activity';
        let detail = a.note || '';
        const typeMatch = detail.match(/^\[([^\]]+)\]\s*(.*)/s);
        if (typeMatch) {
            actType = typeMatch[1];
            detail = typeMatch[2];
        }
        const isBooking = actType === 'Booking';
        const cls = isBooking ? 'activity-entry site-visit' : 'activity-entry note';
        const dateFormatted = fmtDateTime(a.start_date);
        const staff = a.staff || '';
        html += `<div class="${cls}">
            <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold ${isBooking ? 'text-blue-600' : 'text-gray-600'}">${esc(actType)}</span>
                <span class="text-xs text-gray-400">${esc(dateFormatted)}</span>
            </div>
            <div class="text-sm text-gray-700">${esc(staff)}</div>
            ${detail ? `<div class="text-xs text-gray-500 mt-1">${esc(detail)}</div>` : ''}
        </div>`;
    });
    html += `</div>`;
    return html;
}

function renderFiles(files) {
    if (!files || !files.length) return '';
    const photos = files.filter(f => /image|photo|jpg|jpeg|png/i.test(f.type || f.name || ''));
    const docs = files.filter(f => !(/image|photo|jpg|jpeg|png/i.test(f.type || f.name || '')));
    let html = `<div class="modal-section"><h3>Files (${files.length})</h3>`;
    if (photos.length) {
        html += `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">`;
        photos.forEach(p => {
            html += `<a href="/api/sm8-file/${p.uuid}" target="_blank" title="${esc(p.name)}">
                <img src="/api/sm8-file/${p.uuid}" loading="lazy"
                     style="width:80px;height:80px;object-fit:cover;border-radius:6px;border:1px solid rgb(229 231 235)"
                     onerror="this.style.display='none'">
            </a>`;
        });
        html += `</div>`;
    }
    if (docs.length) {
        docs.forEach(d => {
            html += `<div class="text-xs text-gray-500 py-1">&#128196; ${esc(d.name || d.uuid)}</div>`;
        });
    }
    html += `</div>`;
    return html;
}

// --- Deal Detail Modal ---

async function openDealDetail(dealId, e) {
    if (e) e.stopPropagation();
    const res = await fetch(`/api/deal/${dealId}`);
    const data = await res.json();
    if (!data.ok) return;

    const d = data.deal;
    const sm8 = data.sm8 || {};
    const history = data.sync_history || [];
    const projects = data.linked_projects || [];
    // Deduplicate notes by content (keep all types including SM8)
    const _seen = new Set();
    const notes = (data.notes || []).filter(n => {
        const key = (n.content || '').trim().slice(0, 150).toLowerCase();
        if (_seen.has(key)) return false;
        _seen.add(key);
        return true;
    });
    const eod = data.eod || {};
    const activities = data.sm8_activities || [];
    const files = data.sm8_files || [];

    // Find latest site visit for summary
    const siteVisits = activities.filter(a => a.is_site_visit);
    const latestVisit = siteVisits.length ? siteVisits[0] : null;

    let html = `
    <div class="modal-overlay" onclick="closeModal(event)">
        <div class="modal-panel" onclick="event.stopPropagation()">
            <div class="flex items-start justify-between">
                <div>
                    <h2>${esc(d.title)}</h2>
                    <p class="text-xs text-gray-500">${esc(d.pipeline)} · ${esc(d.stage)} · ${fmtVal(d.value)}</p>
                </div>
                <button onclick="closeModal()" class="text-gray-400 hover:text-gray-900 text-lg">&times;</button>
            </div>

            <div class="modal-section">
                <h3>Contact</h3>
                ${d.client ? `<div class="modal-row"><span class="label">Name</span><span class="value">${esc(d.client)}</span></div>` : ''}
                ${d.email ? `<div class="modal-row"><span class="label">Email</span><span class="value">${esc(d.email)}</span></div>` : ''}
                ${d.org ? `<div class="modal-row"><span class="label">Org</span><span class="value">${esc(d.org)}</span></div>` : ''}
                ${d.address || sm8.address ? `<div class="modal-row"><span class="label">Address</span><span class="value">${esc(d.address || sm8.address)}</span></div>` : ''}
            </div>

            <div class="modal-section">
                <h3>ServiceM8</h3>
                ${sm8.sm8_number ? `
                    <div class="modal-row"><span class="label">Job #</span><span class="value">${esc(sm8.sm8_number)}</span></div>
                    <div class="modal-row"><span class="label">Status</span><span class="value">${sm8Badge(sm8.sm8_status)}</span></div>
                    ${latestVisit ? `<div class="modal-row"><span class="label">Site Visit</span><span class="value text-blue-600">${esc(fmtDateShort(latestVisit.start_date))} · ${esc(latestVisit.staff)}</span></div>` : ''}
                    <div class="modal-row"><span class="label">Last synced</span><span class="value">${esc(sm8.last_synced || '—')}</span></div>
                ` : `<p class="text-xs text-gray-400">No SM8 job linked</p>`}
            </div>`;

    // SM8 Activities
    html += renderActivities(activities);

    // SM8 Files
    html += renderFiles(files);

    if (projects.length) {
        html += `<div class="modal-section"><h3>Linked Projects</h3>`;
        projects.forEach(p => {
            html += `<div class="modal-row">
                <span class="label">${esc(p.title)}</span>
                <span class="value">${esc(p.phase)} · ${esc(p.board)}</span>
            </div>`;
        });
        html += `</div>`;
    }

    if (eod.flags?.length || eod.next_action) {
        html += `<div class="modal-section"><h3>Intelligence</h3>`;
        if (eod.next_action) html += `<div class="modal-row"><span class="label">Next action</span><span class="value text-amber-600">${esc(eod.next_action)}</span></div>`;
        if (eod.flags?.length) html += `<div class="modal-row"><span class="label">Flags</span><span class="value text-red-500">${eod.flags.map(f => esc(f)).join('<br>')}</span></div>`;
        html += `</div>`;
    }

    if (notes.length) {
        html += `<div class="modal-section"><h3>Notes (${notes.length})</h3>`;
        notes.forEach(n => {
            const pin = n.pinned ? '<span class="text-amber-500 mr-1" title="Pinned">&#128204;</span>' : '';
            const by = n.user ? `<span class="text-gray-400"> · ${esc(n.user)}</span>` : '';
            const c = (n.content || '').trim();
            // Color-code SM8 notes by type
            let borderColor = 'rgb(229 231 235)';  // default gray
            let labelHtml = '';
            if (c.startsWith('[SM8 Update]')) {
                borderColor = 'rgb(37 99 235)';  // blue
                labelHtml = '<span class="text-xs font-semibold text-blue-600 mr-1">SM8</span>';
            } else if (c.startsWith('[SM8 Booking]') || c.startsWith('[SM8 Site Visit]')) {
                borderColor = 'rgb(147 51 234)';  // purple
                labelHtml = '<span class="text-xs font-semibold text-purple-600 mr-1">SM8</span>';
            } else if (c.startsWith('[SM8 Check Out]') || c.startsWith('[SM8 Check In]')) {
                borderColor = 'rgb(22 163 74)';  // green
                labelHtml = '<span class="text-xs font-semibold text-green-600 mr-1">SM8</span>';
            } else if (c.startsWith('[SM8 Sync]') || c.startsWith('[SM8 Activity]')) {
                borderColor = 'rgb(107 114 128)';  // gray
                labelHtml = '<span class="text-xs font-semibold text-gray-500 mr-1">SM8</span>';
            }
            html += `<div style="margin-bottom:8px;padding:8px 10px;background:rgb(249 250 251);border-radius:6px;border-left:3px solid ${borderColor}">
                <div class="text-xs text-gray-400 mb-1">${labelHtml}${pin}${esc(n.add_time)}${by}</div>
                <div class="text-sm text-gray-700" style="white-space:pre-wrap">${esc(n.content)}</div>
            </div>`;
        });
        html += `</div>`;
    }

    if (history.length) {
        html += `<div class="modal-section"><h3>Sync History</h3>`;
        history.forEach(h => {
            html += `<div class="sync-entry">
                <span class="change">${esc(h.field)}</span>: ${esc(h.old)} → ${esc(h.new)}
                <span class="text-gray-400 ml-1">${esc(h.time)} (${esc(h.source)})</span>
            </div>`;
        });
        html += `</div>`;
    }

    html += `<div class="modal-section text-center">
                <a href="https://epspaintingandcleaning.pipedrive.com/deal/${d.deal_id}" target="_blank"
                   class="text-xs text-blue-600 hover:underline">Open in Pipedrive →</a>
             </div>
        </div>
    </div>`;

    document.getElementById('modal-root').innerHTML = html;
}

// --- Project Detail Modal ---

async function openProjectDetail(projectId, e) {
    if (e) e.stopPropagation();
    const res = await fetch(`/api/project/${projectId}`);
    const data = await res.json();
    if (!data.ok) return;

    const p = data.project;
    const sm8 = data.sm8 || {};
    const activities = data.sm8_activities || [];
    const files = data.sm8_files || [];
    const eod = data.eod || {};

    const siteVisits = activities.filter(a => a.is_site_visit);
    const latestVisit = siteVisits.length ? siteVisits[0] : null;
    const scheduledFuture = siteVisits.find(a => a.start_date > new Date().toISOString());

    let html = `
    <div class="modal-overlay" onclick="closeModal(event)">
        <div class="modal-panel" onclick="event.stopPropagation()">
            <div class="flex items-start justify-between">
                <div>
                    <h2>${esc(p.title)}</h2>
                    <p class="text-xs text-gray-500">${esc(p.board)} · ${esc(p.phase)}</p>
                </div>
                <button onclick="closeModal()" class="text-gray-400 hover:text-gray-900 text-lg">&times;</button>
            </div>

            <div class="modal-section">
                <h3>Project Info</h3>
                <div class="modal-row"><span class="label">Phase</span><span class="value">${esc(p.phase)}</span></div>
                <div class="modal-row"><span class="label">Board</span><span class="value">${esc(p.board)}</span></div>
                <div class="modal-row"><span class="label">Last Update</span><span class="value">${esc(p.last_update)} (${daysText(p.days_since_update)} ago)</span></div>
            </div>

            <div class="modal-section">
                <h3>ServiceM8</h3>
                ${sm8.sm8_number ? `
                    <div class="modal-row"><span class="label">Job #</span><span class="value">${esc(sm8.sm8_number)}</span></div>
                    <div class="modal-row"><span class="label">Status</span><span class="value">${sm8Badge(sm8.sm8_status)}</span></div>
                    ${latestVisit ? `<div class="modal-row"><span class="label">Last Visit</span><span class="value text-blue-600">${esc(fmtDateShort(latestVisit.start_date))} · ${esc(latestVisit.staff)}</span></div>` : ''}
                    ${scheduledFuture ? `<div class="modal-row"><span class="label">Scheduled</span><span class="value text-green-600">${esc(fmtDateShort(scheduledFuture.start_date))} · ${esc(scheduledFuture.staff)}</span></div>` : ''}
                    <div class="modal-row"><span class="label">Last synced</span><span class="value">${esc(sm8.last_synced || '—')}</span></div>
                ` : `<p class="text-xs text-gray-400">No SM8 job linked</p>`}
            </div>`;

    html += renderActivities(activities);
    html += renderFiles(files);

    if (eod.flags?.length || eod.next_action) {
        html += `<div class="modal-section"><h3>Intelligence</h3>`;
        if (eod.next_action) html += `<div class="modal-row"><span class="label">Next action</span><span class="value text-amber-600">${esc(eod.next_action)}</span></div>`;
        if (eod.flags?.length) html += `<div class="modal-row"><span class="label">Flags</span><span class="value text-red-500">${eod.flags.map(f => esc(f)).join('<br>')}</span></div>`;
        html += `</div>`;
    }

    if (data.linked_deal_id) {
        html += `<div class="modal-section text-center">
                    <a href="https://epspaintingandcleaning.pipedrive.com/deal/${data.linked_deal_id}" target="_blank"
                       class="text-xs text-blue-600 hover:underline">Open Deal in Pipedrive →</a>
                 </div>`;
    }

    html += `</div></div>`;

    document.getElementById('modal-root').innerHTML = html;
}

// --- Modal ---

function closeModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('modal-root').innerHTML = '';
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.getElementById('modal-root').innerHTML = '';
});

// --- Init ---

document.addEventListener('DOMContentLoaded', () => {
    if (checkAuth()) switchTab('overview');
});
