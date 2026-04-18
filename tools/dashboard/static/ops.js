// Enriquez OS — Ops cards (PH outreach, US cold calls, Content)
// Pulls from /api/ops/all (and individual endpoints) to render the
// Brand sub-pill on the Work tab, the Outreach tab, and the Content tab.

let _opsCache = null;
let _opsCacheTs = 0;
const OPS_CACHE_TTL = 30000; // 30s

async function fetchOpsAll(force = false) {
    const now = Date.now();
    if (!force && _opsCache && (now - _opsCacheTs) < OPS_CACHE_TTL) {
        return _opsCache;
    }
    try {
        const res = await fetch('/api/ops/all');
        const data = await res.json();
        _opsCache = data;
        _opsCacheTs = now;
        return data;
    } catch (err) {
        console.error('ops/all failed', err);
        return _opsCache;
    }
}

// --- Brand sub-pill: combined ops cards ---
async function loadOpsAll() {
    const container = document.getElementById('ops-cards');
    if (!container) return;
    if (!_opsCache) {
        container.innerHTML = '<div class="text-gray-400 italic text-center py-6 text-sm">Loading...</div>';
    }
    const data = await fetchOpsAll(true);
    if (!data) {
        container.innerHTML = '<div class="text-red-400 text-center py-6 text-sm">Failed to load ops data</div>';
        return;
    }
    container.innerHTML = `
        ${renderOpsCard('PH Outreach', data.ph_outreach, [
            { label: 'Queue', value: data.ph_outreach.queue_size, color: 'text-blue-400' },
            { label: 'Sent today', value: data.ph_outreach.sent_today, color: 'text-emerald-400' },
            { label: 'Replies', value: data.ph_outreach.replies_pending, color: 'text-amber-400' },
        ])}
        ${renderOpsCard('US Cold Calls', data.cold_calls, [
            { label: 'Active', value: data.cold_calls.active_leads, color: 'text-blue-400' },
            { label: 'Due today', value: (data.cold_calls.followups_due_today || []).length, color: 'text-amber-400' },
            { label: 'Replied', value: (data.cold_calls.by_status && data.cold_calls.by_status.replied) || 0, color: 'text-emerald-400' },
        ])}
        ${renderOpsCard('Content', data.content, [
            { label: 'Scripts', value: data.content.scripts_ready, color: 'text-blue-400' },
            { label: 'Recordings', value: data.content.recordings_done, color: 'text-amber-400' },
            { label: 'Posted', value: data.content.published_this_week, color: 'text-emerald-400' },
        ])}
    `;
}

function renderOpsCard(title, payload, stats) {
    const next = (payload && payload.next_action) || '—';
    return `
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div class="text-sm font-semibold text-gray-200 mb-3">${title}</div>
            <div class="grid grid-cols-3 gap-2 mb-3">
                ${stats.map(s => `
                    <div class="bg-gray-950/50 rounded-lg p-2 text-center">
                        <div class="${s.color} text-lg font-bold">${s.value || 0}</div>
                        <div class="text-[10px] text-gray-500 uppercase">${s.label}</div>
                    </div>
                `).join('')}
            </div>
            <div class="text-xs text-gray-400">
                <span class="text-gray-500 uppercase tracking-wider mr-1">Next:</span>${next}
            </div>
        </div>
    `;
}

// --- Outreach tab loader ---
async function loadOutreachOps() {
    const data = await fetchOpsAll(true);
    if (!data) return;

    // Cold Call sub-pill (US painters)
    const cc = data.cold_calls || {};
    setText('cc-active', cc.active_leads || 0);
    const due = cc.followups_due_today || [];
    setText('cc-due', due.length);
    setText('cc-next-action', cc.next_action || '—');
    setText('cc-last-sent', formatTs(cc.last_sent));

    const ccList = document.getElementById('cc-followups');
    if (ccList) {
        if (due.length === 0) {
            ccList.innerHTML = '<div class="text-gray-500 text-center py-4 text-sm">Nothing due today</div>';
        } else {
            ccList.innerHTML = due.map(f => `
                <div class="bg-gray-900 border border-gray-800 rounded-xl px-3 py-2.5">
                    <div class="text-base text-gray-200">
                        ${f.first_name || 'Lead'} <span class="text-gray-500 text-sm">${f.company ? '— ' + f.company : ''}</span>
                    </div>
                    <div class="text-xs text-gray-500 mt-1">Day ${f.day} ${f.email ? '· ' + f.email : ''}</div>
                </div>
            `).join('');
        }
    }

    // Cold DM sub-pill (PH outreach)
    const ph = data.ph_outreach || {};
    setText('ph-queue', ph.queue_size || 0);
    setText('ph-sent', ph.sent_today || 0);
    setText('ph-replies', ph.replies_pending || 0);
    setText('ph-followups-due', ph.followups_due || 0);
    setText('ph-next-action', ph.next_action || '—');
    setText('ph-last-run', formatTs(ph.last_run));
}

// --- Content tab loader ---
async function loadContentOps() {
    const data = await fetchOpsAll(true);
    if (!data) return;
    const c = data.content || {};

    setText('content-scripts', c.scripts_ready || 0);
    setText('content-recordings', c.recordings_done || 0);
    setText('content-posted', c.published_this_week || 0);

    // Pipeline — surface the next-to-film hint (full schedule lives in tracker)
    const pipelineEl = document.getElementById('content-pipeline');
    if (pipelineEl) {
        if (c.next_to_film) {
            pipelineEl.innerHTML = `
                <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Next to Film</div>
                    <div class="text-sm text-gray-200">${c.next_to_film}</div>
                </div>
                <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Next Action</div>
                    <div class="text-sm text-gray-200">${c.next_action || '—'}</div>
                </div>
            `;
        } else {
            pipelineEl.innerHTML = '<div class="text-gray-500 text-center py-6 text-sm">No pipeline items found</div>';
        }
    }

    // Buffer — scripts ready + recordings done counts
    const bufferEl = document.getElementById('content-buffer');
    if (bufferEl) {
        bufferEl.innerHTML = `
            <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 flex items-center justify-between">
                <span class="text-sm text-gray-300">Scripts ready to film</span>
                <span class="text-lg font-bold text-blue-400">${c.scripts_ready || 0}</span>
            </div>
            <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 flex items-center justify-between">
                <span class="text-sm text-gray-300">Recordings ready to edit</span>
                <span class="text-lg font-bold text-amber-400">${c.recordings_done || 0}</span>
            </div>
            <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
                <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Next Action</div>
                <div class="text-sm text-gray-200">${c.next_action || '—'}</div>
            </div>
        `;
    }

    // Published — placeholder (analytics TBD)
    const publishedEl = document.getElementById('content-published');
    if (publishedEl) {
        publishedEl.innerHTML = `
            <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-center">
                <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Posted this week</div>
                <div class="text-2xl font-bold text-emerald-400">${c.published_this_week || 0}</div>
            </div>
        `;
    }
}

// --- helpers ---
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function formatTs(iso) {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return iso;
        return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
        return iso;
    }
}
