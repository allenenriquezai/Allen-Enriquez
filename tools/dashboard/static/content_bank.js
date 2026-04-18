// Content Script Bank — Brand > Content sub-pill v1
// Loads scripts + calendar, supports create/patch/advance-stage.

const CB_STATUSES = ['idea', 'scripted', 'recorded', 'edited', 'posted'];
const CB_PLATFORMS = ['reel', 'youtube', 'carousel'];

const CB_STATUS_COLOR = {
    idea:     { bg: 'bg-gray-700',  text: 'text-gray-200' },
    scripted: { bg: '',             text: 'text-white', style: 'background-color:#02B3E9' },
    recorded: { bg: 'bg-amber-600', text: 'text-white' },
    edited:   { bg: 'bg-teal-600',  text: 'text-white' },
    posted:   { bg: 'bg-emerald-600', text: 'text-white' },
};

const CB_PLATFORM_ICON = { reel: 'RL', youtube: 'YT', carousel: 'CR' };

const cbState = {
    scripts: [],
    counts: { by_status: {}, by_platform: {} },
    filterStatus: 'all',
    filterPlatform: 'all',
    calendarOpen: false,
    calendarLoaded: false,
};

function cbEsc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function loadContentBank() {
    try {
        const res = await fetch('/api/brand/content/scripts');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Load failed');
        cbState.scripts = data.scripts || [];
        cbState.counts = data.counts || { by_status: {}, by_platform: {} };
        cbRenderStats();
        cbRenderFilters();
        cbRenderScripts();
        if (cbState.calendarOpen) loadContentCalendar();
    } catch (e) {
        const el = document.getElementById('cb-scripts');
        if (el) el.innerHTML = `<div class="text-red-400 text-sm italic py-4">Error: ${cbEsc(e.message)}</div>`;
    }
}

function cbRenderStats() {
    const c = cbState.counts.by_status || {};
    CB_STATUSES.forEach(s => {
        const el = document.getElementById(`cb-stat-${s}`);
        if (el) el.textContent = c[s] || 0;
    });
}

function cbRenderFilters() {
    const statusEl = document.getElementById('cb-status-chips');
    if (statusEl) {
        statusEl.innerHTML = ['all', ...CB_STATUSES].map(s => {
            const active = cbState.filterStatus === s;
            const label = s === 'all' ? 'All' : (s[0].toUpperCase() + s.slice(1));
            return `<button onclick="cbSetStatusFilter('${s}')" class="shrink-0 px-2.5 py-1 rounded-md text-[11px] font-medium transition ${active ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}">${label}</button>`;
        }).join('');
    }
    const platEl = document.getElementById('cb-platform-chips');
    if (platEl) {
        platEl.innerHTML = ['all', ...CB_PLATFORMS].map(p => {
            const active = cbState.filterPlatform === p;
            const label = p === 'all' ? 'All' : (p[0].toUpperCase() + p.slice(1));
            return `<button onclick="cbSetPlatformFilter('${p}')" class="shrink-0 px-2.5 py-1 rounded-md text-[11px] font-medium transition ${active ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}">${label}</button>`;
        }).join('');
    }
}

function cbSetStatusFilter(s) { cbState.filterStatus = s; cbRenderFilters(); cbRenderScripts(); }
function cbSetPlatformFilter(p) { cbState.filterPlatform = p; cbRenderFilters(); cbRenderScripts(); }

function cbFilteredScripts() {
    return cbState.scripts.filter(s => {
        if (cbState.filterStatus !== 'all' && s.status !== cbState.filterStatus) return false;
        if (cbState.filterPlatform !== 'all' && s.platform !== cbState.filterPlatform) return false;
        return true;
    });
}

function cbStatusChip(status) {
    const c = CB_STATUS_COLOR[status] || CB_STATUS_COLOR.idea;
    const style = c.style ? `style="${c.style}"` : '';
    return `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${c.bg} ${c.text}" ${style}>${cbEsc(status)}</span>`;
}

function cbRenderScripts() {
    const el = document.getElementById('cb-scripts');
    if (!el) return;
    const scripts = cbFilteredScripts();
    if (!scripts.length) {
        if (!cbState.scripts.length) {
            el.innerHTML = `<div class="text-center py-8">
                <div class="text-gray-500 text-sm mb-3">No scripts yet. Create your first.</div>
                <button onclick="openContentScriptModal()" class="px-4 py-2 rounded-lg text-white text-sm font-medium" style="background-color:#02B3E9">+ New Script</button>
            </div>`;
        } else {
            el.innerHTML = `<div class="text-gray-500 italic text-center py-6 text-sm">No scripts match filters.</div>`;
        }
        return;
    }
    el.innerHTML = scripts.map((s, i) => {
        const legacy = s.source === 'legacy' ? `<span class="ml-1 px-1 py-0.5 rounded text-[9px] bg-gray-700 text-gray-400">LEGACY</span>` : '';
        return `<div onclick="openContentScriptModal(${i})" class="bg-gray-900 border border-gray-800 rounded-lg p-3 active:bg-gray-800 transition cursor-pointer">
            <div class="flex items-start gap-2 mb-1">
                <span class="text-[10px] font-bold text-gray-500 mt-0.5 w-6 shrink-0">${cbEsc(CB_PLATFORM_ICON[s.platform] || '??')}</span>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="text-sm font-semibold text-white truncate">${cbEsc(s.title)}</span>
                        ${cbStatusChip(s.status)}
                        ${legacy}
                    </div>
                    ${s.hook ? `<div class="text-xs text-gray-400 mt-1 line-clamp-2">${cbEsc(s.hook)}</div>` : ''}
                    <div class="text-[10px] text-gray-500 mt-1">${cbEsc(s.created || '')}</div>
                </div>
            </div>
        </div>`;
    }).join('');
}

// ============================================================
// Modal — create / view / edit
// ============================================================

function openContentScriptModal(idx) {
    const modal = document.getElementById('cb-modal');
    const inner = document.getElementById('cb-modal-inner');
    if (!modal || !inner) return;
    const isNew = (idx === undefined || idx === null);
    const scripts = cbFilteredScripts();
    const s = isNew ? null : scripts[idx];

    if (isNew) {
        inner.innerHTML = `
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-bold text-white">New Script</h2>
                <button onclick="closeContentScriptModal()" class="text-gray-400 text-xl leading-none">&times;</button>
            </div>
            <div class="space-y-3">
                <div>
                    <label class="block text-[10px] text-gray-500 uppercase mb-1">Title</label>
                    <input id="cb-new-title" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" placeholder="Hook title">
                </div>
                <div>
                    <label class="block text-[10px] text-gray-500 uppercase mb-1">Hook (one-liner)</label>
                    <input id="cb-new-hook" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" placeholder="Grabber line">
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-[10px] text-gray-500 uppercase mb-1">Platform</label>
                        <select id="cb-new-platform" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white">
                            <option value="reel">Reel</option>
                            <option value="youtube">YouTube</option>
                            <option value="carousel">Carousel</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-[10px] text-gray-500 uppercase mb-1">Status</label>
                        <select id="cb-new-status" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white">
                            ${CB_STATUSES.map(s => `<option value="${s}">${s[0].toUpperCase()+s.slice(1)}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div>
                    <label class="block text-[10px] text-gray-500 uppercase mb-1">Body</label>
                    <textarea id="cb-new-body" rows="8" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" placeholder="Script / outline (markdown ok)"></textarea>
                </div>
                <div class="flex gap-2 pt-2">
                    <button onclick="closeContentScriptModal()" class="flex-1 px-3 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm">Cancel</button>
                    <button onclick="cbSubmitNewScript()" class="flex-1 px-3 py-2 rounded-lg text-white text-sm font-medium" style="background-color:#02B3E9">Save</button>
                </div>
            </div>
        `;
    } else if (s && s.source === 'legacy') {
        inner.innerHTML = `
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-bold text-white">${cbEsc(s.title)}</h2>
                <button onclick="closeContentScriptModal()" class="text-gray-400 text-xl leading-none">&times;</button>
            </div>
            <div class="text-xs text-gray-400 mb-2">${cbStatusChip(s.status)} <span class="ml-1 text-gray-500">${cbEsc(s.platform)}</span></div>
            <div class="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-300 mb-3">${cbEsc(s.body_preview)}</div>
            <div class="text-[11px] text-amber-400 italic">Legacy tracker entry. Migrate to a markdown script to edit.</div>
        `;
    } else if (s) {
        const nextStatus = { idea:'scripted', scripted:'recorded', recorded:'edited', edited:'posted', posted:'posted' }[s.status];
        const canAdvance = s.status !== 'posted';
        inner.innerHTML = `
            <div class="flex items-center justify-between mb-3">
                <h2 class="text-lg font-bold text-white flex-1 pr-3">${cbEsc(s.title)}</h2>
                <button onclick="closeContentScriptModal()" class="text-gray-400 text-xl leading-none">&times;</button>
            </div>
            <div class="flex items-center gap-2 mb-3 flex-wrap">
                ${cbStatusChip(s.status)}
                <span class="text-[10px] text-gray-500 uppercase">${cbEsc(s.platform)}</span>
                ${s.created ? `<span class="text-[10px] text-gray-500">· ${cbEsc(s.created)}</span>` : ''}
                ${s.posted ? `<span class="text-[10px] text-emerald-500">· posted ${cbEsc(s.posted)}</span>` : ''}
            </div>
            ${s.hook ? `<div class="text-sm text-gray-300 mb-3 italic">"${cbEsc(s.hook)}"</div>` : ''}
            <div class="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-200 mb-4 whitespace-pre-wrap max-h-60 overflow-y-auto">${cbEsc(s.body || s.body_preview || '(no body)')}</div>

            <div class="space-y-2 mb-4">
                <div class="text-[10px] text-gray-500 uppercase">Edit</div>
                <div class="grid grid-cols-2 gap-2">
                    <select id="cb-edit-status" class="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white">
                        ${CB_STATUSES.map(st => `<option value="${st}" ${st===s.status?'selected':''}>${st[0].toUpperCase()+st.slice(1)}</option>`).join('')}
                    </select>
                    <select id="cb-edit-platform" class="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white">
                        ${CB_PLATFORMS.map(p => `<option value="${p}" ${p===s.platform?'selected':''}>${p[0].toUpperCase()+p.slice(1)}</option>`).join('')}
                    </select>
                </div>
                <input id="cb-edit-hook" value="${cbEsc(s.hook)}" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white" placeholder="Hook">
                <input id="cb-edit-scheduled" value="${cbEsc(s.scheduled || '')}" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white" placeholder="Scheduled YYYY-MM-DD">
                <button onclick="cbSaveEdits('${cbEsc(s.filename)}')" class="w-full px-3 py-2 rounded-lg bg-gray-700 text-white text-xs font-medium">Save changes</button>
            </div>

            ${canAdvance ? `<button onclick="cbAdvanceStage('${cbEsc(s.filename)}', '${nextStatus}')" class="w-full px-3 py-2 rounded-lg text-white text-sm font-medium" style="background-color:#02B3E9">Advance → ${nextStatus}</button>` : ''}
        `;
    }
    modal.classList.remove('hidden');
}

function closeContentScriptModal() {
    const modal = document.getElementById('cb-modal');
    if (modal) modal.classList.add('hidden');
}

async function cbSubmitNewScript() {
    const title = (document.getElementById('cb-new-title') || {}).value || '';
    const hook = (document.getElementById('cb-new-hook') || {}).value || '';
    const platform = (document.getElementById('cb-new-platform') || {}).value || 'reel';
    const status = (document.getElementById('cb-new-status') || {}).value || 'idea';
    const body = (document.getElementById('cb-new-body') || {}).value || '';
    if (!title.trim()) { alert('Title required'); return; }
    try {
        const res = await fetch('/api/brand/content/scripts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, hook, platform, status, body }),
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Save failed');
        closeContentScriptModal();
        await loadContentBank();
    } catch (e) { alert('Error: ' + e.message); }
}

async function cbPatchScript(filename, patch) {
    const res = await fetch(`/api/brand/content/scripts/${encodeURIComponent(filename)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Patch failed');
    return data;
}

async function cbSaveEdits(filename) {
    const status = (document.getElementById('cb-edit-status') || {}).value;
    const platform = (document.getElementById('cb-edit-platform') || {}).value;
    const hook = (document.getElementById('cb-edit-hook') || {}).value;
    const scheduled = (document.getElementById('cb-edit-scheduled') || {}).value;
    try {
        await cbPatchScript(filename, { status, platform, hook, scheduled });
        closeContentScriptModal();
        await loadContentBank();
    } catch (e) { alert('Error: ' + e.message); }
}

async function cbAdvanceStage(filename, nextStatus) {
    try {
        await cbPatchScript(filename, { status: nextStatus });
        closeContentScriptModal();
        await loadContentBank();
    } catch (e) { alert('Error: ' + e.message); }
}

// ============================================================
// Calendar
// ============================================================

function toggleContentCalendar() {
    cbState.calendarOpen = !cbState.calendarOpen;
    const el = document.getElementById('cb-calendar');
    const tog = document.getElementById('cb-cal-toggle');
    if (!el) return;
    if (cbState.calendarOpen) {
        el.classList.remove('hidden');
        if (tog) tog.textContent = '−';
        if (!cbState.calendarLoaded) loadContentCalendar();
    } else {
        el.classList.add('hidden');
        if (tog) tog.textContent = '+';
    }
}

async function loadContentCalendar() {
    const el = document.getElementById('cb-calendar');
    if (!el) return;
    el.innerHTML = `<div class="text-gray-500 italic text-xs text-center py-3">Loading...</div>`;
    try {
        const res = await fetch('/api/brand/content/calendar');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Load failed');
        cbState.calendarLoaded = true;
        const days = data.days || [];
        if (!days.length) { el.innerHTML = `<div class="text-gray-500 italic text-xs text-center py-3">No dates in range.</div>`; return; }
        el.innerHTML = days.map(d => {
            const dt = new Date(d.date + 'T00:00:00');
            const wd = dt.toLocaleDateString('en-US', { weekday: 'short' });
            const mo = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const items = (d.items || []).map(it => `<span class="inline-block px-1.5 py-0.5 rounded text-[9px] mr-1 mb-1 ${CB_STATUS_COLOR[it.status]?.bg || 'bg-gray-700'} ${CB_STATUS_COLOR[it.status]?.text || 'text-white'}" ${CB_STATUS_COLOR[it.status]?.style ? `style="${CB_STATUS_COLOR[it.status].style}"` : ''}>${cbEsc(CB_PLATFORM_ICON[it.platform] || '?')} ${cbEsc(it.title.slice(0, 30))}</span>`).join('');
            return `<div class="flex gap-2 items-start">
                <div class="w-14 shrink-0 text-[10px] text-gray-500 pt-1">${wd}<br><span class="text-gray-400">${mo}</span></div>
                <div class="flex-1 bg-gray-900 border border-gray-800 rounded-lg p-2 min-h-[32px]">
                    ${items || '<span class="text-[10px] text-gray-600 italic">—</span>'}
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        el.innerHTML = `<div class="text-red-400 text-xs italic py-3">Error: ${cbEsc(e.message)}</div>`;
    }
}
