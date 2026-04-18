// Brand > Outcomes — feedback-loop dashboard panel.

const OC_COLORS = {
    primary: '#02B3E9',
    warn: '#FF9B28',
    surface: '#13334A',
    border: '#25373C',
};

function ocEsc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function ocFmtPct(rate) {
    if (rate === null || rate === undefined) return '--';
    return `${Math.round(rate * 100)}%`;
}

function ocRateColor(rate) {
    if (rate === null || rate === undefined) return 'text-gray-400';
    if (rate >= 0.20) return 'text-emerald-400';
    if (rate >= 0.10) return 'text-[#02B3E9]';
    if (rate >= 0.05) return 'text-[#FF9B28]';
    return 'text-red-400';
}

function ocResultBadge(result) {
    const r = (result || 'pending').toLowerCase();
    const map = {
        won:            ['Won',           'bg-emerald-900/40 text-emerald-300 border-emerald-700/50'],
        replied:        ['Replied',       'bg-cyan-900/40 text-cyan-300 border-cyan-700/50'],
        stage_changed:  ['Stage Changed', 'bg-cyan-900/40 text-cyan-300 border-cyan-700/50'],
        lost:           ['Lost',          'bg-red-900/40 text-red-300 border-red-700/50'],
        no_change:      ['No Reply',      'bg-gray-800/60 text-gray-400 border-gray-700/50'],
        pending:        ['Pending',       'bg-amber-900/40 text-amber-300 border-amber-700/50'],
    };
    const [label, cls] = map[r] || [r, 'bg-gray-800/60 text-gray-400 border-gray-700/50'];
    return `<span class="inline-block px-2 py-0.5 rounded text-[10px] border ${cls}">${ocEsc(label)}</span>`;
}

function ocShortTs(iso) {
    if (!iso) return '--';
    try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return iso.slice(0, 16);
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const hh = String(d.getHours()).padStart(2, '0');
        const mi = String(d.getMinutes()).padStart(2, '0');
        return `${mm}-${dd} ${hh}:${mi}`;
    } catch { return iso; }
}

function ocToast(msg, type) {
    const existing = document.getElementById('oc-toast');
    if (existing) existing.remove();
    const el = document.createElement('div');
    el.id = 'oc-toast';
    const bg = type === 'error' ? 'bg-red-900 border-red-700' : 'bg-emerald-900 border-emerald-700';
    el.className = `fixed bottom-20 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg text-sm border ${bg} text-white shadow-lg z-50`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2200);
}

// ------------------------------------------------------------
// Hero stats — compute from summary.by_action
// ------------------------------------------------------------

function ocComputeOverall(summary) {
    // Weighted mean across actions that report the rate.
    const by = summary.by_action || {};
    let replyCheckedTot = 0, replyGoodTot = 0, replyN = 0;
    let winCheckedTot = 0, winGoodTot = 0, winN = 0;
    let totalLogged = 0;

    Object.entries(by).forEach(([action, stats]) => {
        const total = stats.total ?? stats.logged ?? 0;
        const pending = stats.pending ?? 0;
        const checked = Math.max(0, total - pending);
        totalLogged += total;
        if (stats.reply_rate !== undefined && stats.reply_rate !== null) {
            const replied = stats.replied ?? Math.round(stats.reply_rate * checked);
            replyCheckedTot += checked;
            replyGoodTot += replied;
            replyN += total;
        }
        if (stats.win_rate !== undefined && stats.win_rate !== null) {
            const won = stats.won ?? Math.round(stats.win_rate * checked);
            winCheckedTot += checked;
            winGoodTot += won;
            winN += total;
        }
    });

    const overallReply = replyCheckedTot > 0 ? replyGoodTot / replyCheckedTot : null;
    const overallWin = winCheckedTot > 0 ? winGoodTot / winCheckedTot : null;
    return {
        reply: overallReply,
        replySample: replyN,
        win: overallWin,
        winSample: winN,
        totalLogged,
    };
}

// ------------------------------------------------------------
// Renderers
// ------------------------------------------------------------

function renderHeroStats(summary) {
    const reply = document.getElementById('oc-reply-rate');
    const win = document.getElementById('oc-win-rate');
    if (!reply || !win) return;

    const stats = ocComputeOverall(summary);

    reply.innerHTML = `
        <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Overall Reply Rate (30d)</div>
        <div class="text-3xl font-bold ${ocRateColor(stats.reply)}">${ocFmtPct(stats.reply)}</div>
        <div class="text-[11px] text-gray-500 mt-1">n=${stats.replySample}</div>
    `;
    win.innerHTML = `
        <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Overall Win Rate (30d)</div>
        <div class="text-3xl font-bold ${ocRateColor(stats.win)}">${ocFmtPct(stats.win)}</div>
        <div class="text-[11px] text-gray-500 mt-1">n=${stats.winSample}</div>
    `;
}

function renderByAction(summary) {
    const box = document.getElementById('oc-by-action');
    if (!box) return;
    const by = summary.by_action || {};
    const entries = Object.entries(by);
    if (!entries.length) {
        box.innerHTML = '<div class="text-xs text-gray-500 italic px-3 py-2">No action breakdown yet.</div>';
        return;
    }
    const rows = entries.map(([action, s]) => {
        const logged = s.total ?? s.logged ?? 0;
        const reply = s.reply_rate;
        const win = s.win_rate;
        return `
            <div class="flex items-center justify-between py-2 border-b border-[#25373C] last:border-b-0">
                <div class="flex-1 min-w-0">
                    <div class="text-sm text-gray-200 font-medium truncate">${ocEsc(action)}</div>
                    <div class="text-[10px] text-gray-500">logged: ${logged}</div>
                </div>
                <div class="flex gap-4 text-right ml-2">
                    <div>
                        <div class="text-[10px] text-gray-500 uppercase">Reply</div>
                        <div class="text-sm font-semibold ${ocRateColor(reply)}">${ocFmtPct(reply)}</div>
                    </div>
                    <div>
                        <div class="text-[10px] text-gray-500 uppercase">Win</div>
                        <div class="text-sm font-semibold ${ocRateColor(win)}">${ocFmtPct(win)}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    box.innerHTML = rows;
}

function renderTopTemplates(summary) {
    const box = document.getElementById('oc-top-templates');
    if (!box) return;
    const tops = summary.top_templates || [];
    if (!tops.length) {
        box.innerHTML = '<div class="text-xs text-gray-500 italic px-3 py-2">No template data yet.</div>';
        return;
    }
    const rows = tops.map(t => `
        <div class="flex items-center justify-between py-2 border-b border-[#25373C] last:border-b-0">
            <div class="flex-1 min-w-0">
                <div class="text-sm text-gray-200 font-medium truncate">${ocEsc(t.template || '--')}</div>
                <div class="text-[10px] text-gray-500">${ocEsc(t.channel || t.action || '')}</div>
            </div>
            <div class="flex gap-4 text-right ml-2">
                <div>
                    <div class="text-[10px] text-gray-500 uppercase">Reply</div>
                    <div class="text-sm font-semibold ${ocRateColor(t.reply_rate)}">${ocFmtPct(t.reply_rate)}</div>
                </div>
                <div>
                    <div class="text-[10px] text-gray-500 uppercase">N</div>
                    <div class="text-sm font-semibold text-gray-300">${t.sample ?? t.n ?? 0}</div>
                </div>
            </div>
        </div>
    `).join('');
    box.innerHTML = rows;
}

function renderFlags(flags) {
    const box = document.getElementById('oc-flags');
    if (!box) return;
    if (!flags || !flags.length) {
        box.innerHTML = `
            <div class="text-xs text-gray-500 italic px-3 py-4 text-center">
                No pattern suggestions. The system will surface them after enough data.
            </div>
        `;
        return;
    }
    box.innerHTML = flags.map(f => {
        const evidence = Array.isArray(f.evidence) ? f.evidence.slice(0, 2) : [];
        const evidenceHtml = evidence.length
            ? `<div class="mt-2 space-y-1">
                ${evidence.map(ev => `<div class="text-[11px] text-gray-500 pl-3 border-l border-[#25373C]">${ocEsc(typeof ev === 'string' ? ev : JSON.stringify(ev))}</div>`).join('')}
               </div>`
            : '';
        const suggestion = f.suggested_change || f.suggestion || '';
        const pattern = f.pattern || f.description || '';
        return `
            <div data-flag-id="${ocEsc(f.id)}" class="bg-[#13334A]/40 border border-[#25373C] rounded-lg p-3 mb-2">
                <div class="text-xs text-[#02B3E9] uppercase tracking-wider mb-1">Pattern detected</div>
                <div class="text-sm text-gray-100 font-medium mb-1">${ocEsc(pattern)}</div>
                ${f.target_file ? `<div class="text-[10px] text-gray-500 font-mono mb-2">${ocEsc(f.target_file)}</div>` : ''}
                ${suggestion ? `<div class="text-xs text-gray-300 mb-1"><span class="text-gray-500">Suggestion:</span> ${ocEsc(suggestion)}</div>` : ''}
                ${evidenceHtml}
                <div class="flex gap-2 mt-3">
                    <button onclick="ocFlagAction('${ocEsc(f.id)}','accept')"
                            class="flex-1 text-xs bg-emerald-900/50 hover:bg-emerald-800/70 border border-emerald-700/50 text-emerald-200 py-1.5 rounded transition">
                        Accept
                    </button>
                    <button onclick="ocFlagAction('${ocEsc(f.id)}','dismiss')"
                            class="flex-1 text-xs bg-gray-800/60 hover:bg-gray-700/70 border border-gray-700 text-gray-300 py-1.5 rounded transition">
                        Dismiss
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderEvents(events) {
    const box = document.getElementById('oc-events');
    if (!box) return;
    if (!events || !events.length) {
        box.innerHTML = '<div class="text-xs text-gray-500 italic px-3 py-2">No events yet.</div>';
        return;
    }
    box.innerHTML = events.map(e => {
        const target = e.detail || e.target || e.ref || '';
        return `
            <div class="flex items-center gap-2 py-1.5 border-b border-[#25373C] last:border-b-0 text-xs">
                <div class="text-gray-500 w-20 flex-shrink-0 font-mono text-[10px]">${ocShortTs(e.ts || e.timestamp)}</div>
                <div class="text-gray-300 w-24 flex-shrink-0 truncate">${ocEsc(e.action || '')}</div>
                <div class="text-gray-400 flex-1 min-w-0 truncate">${ocEsc(target)}</div>
                <div class="flex-shrink-0">${ocResultBadge(e.result)}</div>
            </div>
        `;
    }).join('');
}

// ------------------------------------------------------------
// Flag actions
// ------------------------------------------------------------

async function ocFlagAction(flagId, action) {
    try {
        const res = await fetch(`/api/brand/outcomes/flags/${encodeURIComponent(flagId)}/${action}`, {
            method: 'POST',
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Request failed');

        // Remove card from DOM without reload.
        const card = document.querySelector(`[data-flag-id="${flagId}"]`);
        if (card) card.remove();

        ocToast(action === 'accept' ? 'Flag accepted' : 'Dismissed', 'ok');

        // If no flags left, show empty state.
        const box = document.getElementById('oc-flags');
        if (box && !box.querySelector('[data-flag-id]')) {
            renderFlags([]);
        }
    } catch (e) {
        ocToast(`Error: ${e.message}`, 'error');
    }
}

// ------------------------------------------------------------
// Entry point
// ------------------------------------------------------------

async function loadOutcomes() {
    const summaryBox = document.getElementById('oc-by-action');
    if (summaryBox) summaryBox.innerHTML = '<div class="text-xs text-gray-400 italic px-3 py-2">Loading...</div>';

    try {
        const [sumRes, flagsRes, eventsRes] = await Promise.all([
            fetch('/api/brand/outcomes/summary'),
            fetch('/api/brand/outcomes/flags'),
            fetch('/api/brand/outcomes/events?limit=20'),
        ]);
        const [sum, flags, events] = await Promise.all([sumRes.json(), flagsRes.json(), eventsRes.json()]);

        // Summary — either exists or not.
        if (!sum.exists) {
            const reply = document.getElementById('oc-reply-rate');
            const win = document.getElementById('oc-win-rate');
            if (reply) reply.innerHTML = `<div class="text-xs text-gray-500 italic">${ocEsc(sum.reason || 'No data yet.')}</div>`;
            if (win) win.innerHTML = '';
            const by = document.getElementById('oc-by-action');
            if (by) by.innerHTML = `
                <div class="text-xs text-gray-500 italic px-3 py-4 text-center">
                    No outcomes tracked yet. Run: <code class="text-[#02B3E9]">python3 tools/check_outcomes.py</code> after you have outreach activity.
                </div>`;
            const top = document.getElementById('oc-top-templates');
            if (top) top.innerHTML = '';
        } else {
            renderHeroStats(sum);
            renderByAction(sum);
            renderTopTemplates(sum);
        }

        renderFlags(flags.flags || []);
        renderEvents(events.events || []);
    } catch (e) {
        const by = document.getElementById('oc-by-action');
        if (by) by.innerHTML = `<div class="text-xs text-red-400 px-3 py-2">Error: ${ocEsc(e.message)}</div>`;
    }
}

// Collapse toggle for events section.
function ocToggleEvents() {
    const body = document.getElementById('oc-events-body');
    const caret = document.getElementById('oc-events-caret');
    if (!body) return;
    const hidden = body.classList.toggle('hidden');
    if (caret) caret.textContent = hidden ? '+' : '-';
}

window.loadOutcomes = loadOutcomes;
window.ocFlagAction = ocFlagAction;
window.ocToggleEvents = ocToggleEvents;
