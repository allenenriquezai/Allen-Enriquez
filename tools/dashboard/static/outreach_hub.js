// Outreach Hub v1 — prospect list + pipeline + templates for Brand > Outreach.
//
// Entry: loadOutreachHub()
// Replaces the old loadOutreachOps counter-only panel.

const OH_BLUE = '#02B3E9';
const OH_ORANGE = '#FF9B28';
const OH_CARD = '#13334A';
const OH_BORDER = '#25373C';

const OH_CHANNELS = [
    { key: 'all',      label: 'All',        active: true },
    { key: 'fb_group', label: 'FB Groups',  active: true },
    { key: 'fb_dm',    label: 'FB DM',      active: true },
    { key: 'ig',       label: 'IG',         active: false, tip: 'Coming in Phase 2' },
    { key: 'tiktok',   label: 'TikTok',     active: false, tip: 'Coming in Phase 2' },
    { key: 'email',    label: 'Email',      active: false, tip: 'Coming in Phase 2' },
];

const OH_STAGES = [
    { key: 'all',       label: 'All' },
    { key: 'discover',  label: 'Discover' },
    { key: 'enrich',    label: 'Enrich' },
    { key: 'messaged',  label: 'Messaged' },
    { key: 'replied',   label: 'Replied' },
    { key: 'booked',    label: 'Booked' },
    { key: 'cold',      label: 'Cold' },
];

const ohState = {
    channel: 'all',
    stage: 'all',
    prospects: [],
    counts: { by_stage: {}, by_channel: {} },
    pipelineOpen: true,
};

function ohEscape(s) {
    return String(s || '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function ohChannelIcon(channel) {
    if (channel === 'fb_group') return '👥';
    if (channel === 'fb_dm') return '💬';
    if (channel === 'ig') return '📷';
    if (channel === 'tiktok') return '🎵';
    if (channel === 'email') return '✉️';
    return '·';
}

function ohStageColor(stage) {
    switch (stage) {
        case 'replied': return OH_ORANGE;
        case 'messaged': return OH_BLUE;
        case 'booked': return '#10B981';
        case 'cold': return '#6B7280';
        case 'enrich': return '#A78BFA';
        default: return '#9CA3AF';
    }
}

function ohStageChipHtml(stage) {
    const color = ohStageColor(stage);
    const label = (OH_STAGES.find(s => s.key === stage) || {}).label || stage;
    return `<span class="inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded" style="background:${color}20;color:${color};border:1px solid ${color}40;font-family:ui-monospace,Menlo,monospace">${ohEscape(label)}</span>`;
}

function ohToast(msg) {
    const t = document.getElementById('oh-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 2400);
}

// ---- Chips ----

function ohRenderChannelChips() {
    const c = document.getElementById('oh-channel-chips');
    if (!c) return;
    const cc = ohState.counts.by_channel || {};
    c.innerHTML = OH_CHANNELS.map(ch => {
        const active = ohState.channel === ch.key;
        const count = ch.key === 'all'
            ? (Object.values(cc).reduce((a, b) => a + (b || 0), 0))
            : (cc[ch.key] || 0);
        const disabled = !ch.active;
        const base = 'px-3 py-1.5 rounded-lg text-xs font-medium transition shrink-0';
        const style = active
            ? `background:${OH_BLUE};color:#031019`
            : disabled
                ? `background:#1F2937;color:#6B7280;cursor:not-allowed;opacity:0.55`
                : `background:#1F2937;color:#9CA3AF`;
        const onclick = disabled ? '' : `onclick="ohSetChannel('${ch.key}')"`;
        const tip = disabled ? `title="${ohEscape(ch.tip || '')}"` : '';
        const countBadge = (ch.key !== 'all' || count > 0)
            ? ` <span class="opacity-70">(${count})</span>` : '';
        return `<button class="${base}" style="${style};font-family:ui-monospace,Menlo,monospace" ${onclick} ${tip}>${ohEscape(ch.label)}${countBadge}</button>`;
    }).join('');
}

function ohRenderStageChips() {
    const c = document.getElementById('oh-stage-chips');
    if (!c) return;
    const sc = ohState.counts.by_stage || {};
    c.innerHTML = OH_STAGES.map(st => {
        const active = ohState.stage === st.key;
        const count = st.key === 'all'
            ? (Object.values(sc).reduce((a, b) => a + (b || 0), 0))
            : (sc[st.key] || 0);
        const stageColor = st.key === 'all' ? OH_BLUE : ohStageColor(st.key);
        const base = 'px-3 py-1.5 rounded-lg text-xs font-medium transition shrink-0';
        const style = active
            ? `background:${stageColor};color:#031019`
            : `background:#1F2937;color:#9CA3AF`;
        return `<button class="${base}" style="${style};font-family:ui-monospace,Menlo,monospace" onclick="ohSetStage('${st.key}')">${ohEscape(st.label)} <span class="opacity-70">(${count})</span></button>`;
    }).join('');
}

function ohSetChannel(ch) { ohState.channel = ch; ohLoadProspects(); }
function ohSetStage(st) { ohState.stage = st; ohLoadProspects(); }

// ---- Stats ----

function ohUpdateStats() {
    const sc = ohState.counts.by_stage || {};
    const q = document.getElementById('oh-stat-queue');
    const s = document.getElementById('oh-stat-sent');
    const r = document.getElementById('oh-stat-replies');
    const b = document.getElementById('oh-stat-booked');
    // Queue = discover + enrich (not yet sent)
    const queue = (sc.discover || 0) + (sc.enrich || 0);
    // Sent today: count prospects with last_touch_date == today
    const todayStr = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
    const sentToday = ohState.prospects.filter(p => p.last_touch_date === todayStr).length;
    if (q) q.textContent = queue;
    if (s) s.textContent = sentToday;
    if (r) r.textContent = (sc.replied || 0);
    if (b) b.textContent = (sc.booked || 0);
}

// ---- Prospects ----

async function ohLoadProspects() {
    const list = document.getElementById('oh-prospects');
    const count = document.getElementById('oh-prospects-count');
    if (!list) return;
    list.innerHTML = '<div class="text-gray-400 italic text-center py-8 text-sm">Loading prospects...</div>';
    try {
        const url = `/api/brand/outreach/prospects?channel=${ohState.channel}&stage=${ohState.stage}&limit=100`;
        const res = await fetch(url);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Prospects failed');
        ohState.prospects = data.prospects || [];
        ohState.counts = data.counts || { by_stage: {}, by_channel: {} };
        ohRenderChannelChips();
        ohRenderStageChips();
        ohUpdateStats();

        if (count) count.textContent = `${ohState.prospects.length} shown`;

        if (!ohState.prospects.length) {
            const hint = ohState.stage === 'all' && ohState.channel === 'all'
                ? 'No prospects yet. Run <code class="text-[#02B3E9]">python3 tools/outreach.py discover</code>'
                : `No prospects in this filter. Add one via <code class="text-[#02B3E9]">python3 tools/outreach.py enrich</code>`;
            list.innerHTML = `<div class="rounded-xl p-6 text-center text-sm text-gray-400 border" style="background:${OH_CARD};border-color:${OH_BORDER}">${hint}</div>`;
            return;
        }

        list.innerHTML = ohState.prospects.map((p, i) => {
            const icon = ohChannelIcon(p.channel);
            const overdue = p.next_action && /overdue|due 20/i.test(p.next_action);
            const actionColor = overdue ? OH_ORANGE : '#9CA3AF';
            return `<div class="rounded-xl p-3 border flex items-center gap-3 cursor-pointer hover:brightness-110 transition"
                         style="background:${OH_CARD};border-color:${OH_BORDER}"
                         onclick="ohOpenProspect(${i})">
                <div class="text-xl min-w-[24px] text-center">${icon}</div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-sm font-semibold text-gray-100 truncate">${ohEscape(p.name)}</span>
                        ${ohStageChipHtml(p.stage)}
                    </div>
                    <div class="flex items-center gap-2 text-[11px]" style="color:#9CA3AF">
                        <span>${p.last_touch_date ? 'Last: ' + ohEscape(p.last_touch_date) : 'Not contacted'}</span>
                        <span>·</span>
                        <span style="color:${actionColor}">${ohEscape(p.next_action || '—')}</span>
                    </div>
                </div>
                <div class="text-sm" style="color:${OH_BLUE}">→</div>
            </div>`;
        }).join('');
    } catch (e) {
        list.innerHTML = `<div class="rounded-xl p-4 text-center text-sm border" style="background:${OH_CARD};border-color:${OH_BORDER};color:${OH_ORANGE}">Failed to load prospects: ${ohEscape(e.message)}</div>`;
    }
}

// ---- Pipeline ----

function toggleOutreachPipeline() {
    ohState.pipelineOpen = !ohState.pipelineOpen;
    const pane = document.getElementById('oh-pipeline');
    const caret = document.getElementById('oh-pipeline-caret');
    if (pane) pane.classList.toggle('hidden', !ohState.pipelineOpen);
    if (caret) caret.textContent = ohState.pipelineOpen ? '▼' : '▶';
}

async function ohLoadPipeline() {
    const pane = document.getElementById('oh-pipeline');
    if (!pane) return;
    pane.innerHTML = '<div class="text-gray-400 italic text-center py-6 text-sm w-full">Loading pipeline...</div>';
    try {
        const res = await fetch('/api/brand/outreach/pipeline');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Pipeline failed');
        const lanes = data.lanes || [];
        if (!lanes.length) {
            pane.innerHTML = `<div class="text-gray-400 italic text-center py-6 text-sm w-full">Empty pipeline.</div>`;
            return;
        }
        pane.innerHTML = lanes.map(lane => {
            const color = ohStageColor(lane.stage);
            const items = (lane.prospects || []).map(p => `
                <div class="rounded-md p-2 text-[11px] border mb-1.5" style="background:#0B1E2E;border-color:${OH_BORDER}">
                    <div class="font-semibold text-gray-100 truncate">${ohEscape(p.name)}</div>
                    <div class="text-gray-500 truncate">${p.last_touch_date ? ohEscape(p.last_touch_date) : '—'}</div>
                </div>
            `).join('') || `<div class="text-[11px] text-gray-500 italic">Empty</div>`;
            return `<div class="shrink-0 rounded-xl p-3 border" style="width:180px;background:${OH_CARD};border-color:${OH_BORDER}">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-[10px] uppercase tracking-wider" style="color:${color};font-family:ui-monospace,Menlo,monospace">${ohEscape(lane.label)}</span>
                    <span class="text-[10px] text-gray-400">${lane.count}</span>
                </div>
                ${items}
            </div>`;
        }).join('');
    } catch (e) {
        pane.innerHTML = `<div class="text-sm w-full text-center py-4" style="color:${OH_ORANGE}">Pipeline error: ${ohEscape(e.message)}</div>`;
    }
}

// ---- Templates ----

async function ohLoadTemplates() {
    const pane = document.getElementById('oh-templates');
    if (!pane) return;
    pane.innerHTML = '<div class="text-gray-400 italic text-center py-6 text-sm">Loading templates...</div>';
    try {
        const res = await fetch('/api/brand/outreach/templates');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Templates failed');
        const tpls = data.templates || [];
        if (!tpls.length) {
            pane.innerHTML = `<div class="rounded-xl p-4 text-center text-sm text-gray-400 border" style="background:${OH_CARD};border-color:${OH_BORDER}">No templates found. Add files to <code class="text-[#02B3E9]">projects/personal/templates/outreach/</code></div>`;
            return;
        }
        pane.innerHTML = tpls.map((t, i) => {
            const chIcon = ohChannelIcon(t.channel);
            const sub = t.last_used ? `Last used ${ohEscape(t.last_used)}` : 'Never used';
            return `<div class="rounded-xl p-3 border flex items-center gap-3" style="background:${OH_CARD};border-color:${OH_BORDER}">
                <div class="text-lg min-w-[24px] text-center">${chIcon}</div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-semibold text-gray-100 truncate">${ohEscape(t.name)}</div>
                    <div class="text-[11px] text-gray-500">${sub} · ${t.use_count} uses</div>
                </div>
                <button class="px-3 py-1.5 rounded-lg text-xs" style="background:${OH_BLUE};color:#031019;font-family:ui-monospace,Menlo,monospace"
                        onclick='ohCopyTemplate(${JSON.stringify(t.preview)})'>Copy</button>
            </div>`;
        }).join('');
    } catch (e) {
        pane.innerHTML = `<div class="text-sm text-center py-4" style="color:${OH_ORANGE}">Templates error: ${ohEscape(e.message)}</div>`;
    }
}

function ohCopyTemplate(preview) {
    try {
        navigator.clipboard.writeText(preview || '');
        ohToast('Template preview copied');
    } catch {
        ohToast('Copy failed — select manually');
    }
}

// ---- Modal ----

function ohOpenProspect(idx) {
    const p = ohState.prospects[idx];
    if (!p) return;
    const body = document.getElementById('oh-modal-body');
    const modal = document.getElementById('oh-modal');
    if (!body || !modal) return;

    const touchesHtml = [1, 2, 3].map(n => {
        const d = p.touches && p.touches[`t${n}_date`];
        const tpl = p.touches && p.touches[`t${n}_template`];
        const hasData = d || tpl;
        return `<div class="rounded-md p-2 border mb-1.5" style="background:#0B1E2E;border-color:${OH_BORDER}">
            <div class="text-[10px] uppercase tracking-wider" style="color:${OH_BLUE};font-family:ui-monospace,Menlo,monospace">Touch ${n}</div>
            <div class="text-xs text-gray-200 mt-0.5">${hasData ? `${ohEscape(d || '—')} · ${ohEscape(tpl || '—')}` : 'Not sent'}</div>
        </div>`;
    }).join('');

    body.innerHTML = `
        <div class="flex items-start justify-between mb-3">
            <div>
                <div class="text-lg font-bold text-white">${ohEscape(p.name)}</div>
                <div class="flex gap-2 items-center mt-1">
                    ${ohStageChipHtml(p.stage)}
                    <span class="text-[10px] text-gray-400">${ohEscape(p.channel)} · ${ohEscape(p.segment || 'no segment')}</span>
                </div>
            </div>
            <button onclick="closeOutreachModal()" class="text-gray-400 hover:text-white text-2xl leading-none">×</button>
        </div>
        ${p.fb_url ? `<a href="${ohEscape(p.fb_url)}" target="_blank" rel="noopener"
            class="block text-xs mb-3 underline truncate" style="color:${OH_BLUE}">${ohEscape(p.fb_url)}</a>` : ''}
        <div class="rounded-md p-2 border mb-3" style="background:#0B1E2E;border-color:${OH_BORDER}">
            <div class="text-[10px] uppercase tracking-wider" style="color:${OH_ORANGE};font-family:ui-monospace,Menlo,monospace">Next action</div>
            <div class="text-sm text-gray-100 mt-0.5">${ohEscape(p.next_action || '—')}</div>
        </div>
        <div class="mb-3">${touchesHtml}</div>
        ${p.reply_snippet ? `<div class="rounded-md p-2 border mb-3" style="background:#0B1E2E;border-color:${OH_BORDER}">
            <div class="text-[10px] uppercase tracking-wider" style="color:${OH_BLUE};font-family:ui-monospace,Menlo,monospace">Reply</div>
            <div class="text-xs text-gray-200 mt-0.5">${ohEscape(p.reply_snippet)}</div>
        </div>` : ''}
        ${p.notes ? `<div class="rounded-md p-2 border mb-3" style="background:#0B1E2E;border-color:${OH_BORDER}">
            <div class="text-[10px] uppercase tracking-wider text-gray-400" style="font-family:ui-monospace,Menlo,monospace">Notes</div>
            <div class="text-xs text-gray-200 mt-0.5">${ohEscape(p.notes)}</div>
        </div>` : ''}
        <div class="flex gap-2 mt-4">
            <button onclick="ohMarkSent()" class="flex-1 px-3 py-2 rounded-lg text-sm font-medium"
                    style="background:${OH_BLUE};color:#031019;font-family:ui-monospace,Menlo,monospace">Mark Sent</button>
            <button onclick="ohDraftReply()" class="flex-1 px-3 py-2 rounded-lg text-sm font-medium"
                    style="background:#1F2937;color:#E5E7EB;font-family:ui-monospace,Menlo,monospace">Draft Reply</button>
        </div>
    `;
    modal.classList.remove('hidden');
}

function closeOutreachModal(event) {
    if (event && event.target && event.target.id !== 'oh-modal') return;
    const modal = document.getElementById('oh-modal');
    if (modal) modal.classList.add('hidden');
}

function ohMarkSent() {
    ohToast('Manual send from queue file for now');
    closeOutreachModal();
}

function ohDraftReply() {
    ohToast('Draft Reply coming soon — run tools/outreach.py reply');
    closeOutreachModal();
}

// ---- Entry ----

async function loadOutreachHub() {
    // Render initial chip bars immediately so filters respond fast
    ohRenderChannelChips();
    ohRenderStageChips();
    await ohLoadProspects();
    ohLoadPipeline();
    ohLoadTemplates();
}
