// Enriquez OS — Brief tab JS
// Sub-nav pills: EPS / Personal / AI Learning
// Auto-refreshes every 60s

let activeBrief = 'eps';
let briefRefreshTimer = null;
let briefCache = {};

function switchBrief(section) {
    activeBrief = section;

    // Update pill styles
    document.querySelectorAll('.brief-pill').forEach(pill => {
        if (pill.dataset.section === section) {
            pill.classList.remove('bg-gray-800', 'text-gray-400');
            pill.classList.add('bg-blue-600', 'text-white');
        } else {
            pill.classList.remove('bg-blue-600', 'text-white');
            pill.classList.add('bg-gray-800', 'text-gray-400');
        }
    });

    // Hide all brief sections, show selected
    document.querySelectorAll('.brief-section').forEach(s => s.classList.add('hidden'));
    const el = document.getElementById(`brief-${section}`);
    if (el) el.classList.remove('hidden');

    // Load data if not cached
    loadBrief(section);
}

function loadBrief(section) {
    const container = document.getElementById(`brief-${section}`);
    if (!container) return;

    // Show loading only if no cached content
    if (!briefCache[section]) {
        container.innerHTML = '<div class="text-gray-500 text-center py-8 text-sm">Loading...</div>';
    }

    fetch(`/api/brief/${section}`)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                container.innerHTML = `<div class="text-red-400 text-center py-8 text-sm">Error: ${data.error}</div>`;
                return;
            }
            briefCache[section] = data;
            if (section === 'eps') renderEps(container, data);
            else if (section === 'personal') renderPersonal(container, data);
            else if (section === 'learning') renderLearning(container, data);
        })
        .catch(() => {
            if (!briefCache[section]) {
                container.innerHTML = '<div class="text-red-400 text-center py-8 text-sm">Failed to load</div>';
            }
        });
}

function prefetchBriefs() {
    ['eps', 'personal'].forEach(section => {
        if (!briefCache[section]) {
            fetch(`/api/brief/${section}`)
                .then(r => r.json())
                .then(data => { if (data.ok) briefCache[section] = data; })
                .catch(() => {});
        }
    });
}

function refreshBrief() {
    // Force clear cache and re-fetch current section
    const btn = document.getElementById('brief-refresh-btn');
    if (btn) { btn.textContent = '...'; btn.disabled = true; }
    briefCache[activeBrief] = null;
    loadBrief(activeBrief);
    setTimeout(() => { if (btn) { btn.textContent = 'Refresh'; btn.disabled = false; } }, 1000);
}

function loadLearning() {
    const container = document.getElementById('brief-learning');
    if (!container) return;
    if (briefCache['learning']) {
        renderLearning(container, briefCache['learning']);
        return;
    }
    container.innerHTML = '<div class="text-gray-500 text-center py-8 text-sm">Loading...</div>';
    fetch('/api/brief/learning')
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                container.innerHTML = `<div class="text-red-400 text-center py-8 text-sm">Error: ${data.error}</div>`;
                return;
            }
            briefCache['learning'] = data;
            renderLearning(container, data);
        })
        .catch(() => {
            if (!briefCache['learning']) {
                container.innerHTML = '<div class="text-red-400 text-center py-8 text-sm">Failed to load</div>';
            }
        });
}

function refreshLearning() {
    const btn = document.getElementById('learn-refresh-btn');
    if (btn) { btn.textContent = '...'; btn.disabled = true; }
    briefCache['learning'] = null;
    loadLearning();
    setTimeout(() => { if (btn) { btn.textContent = 'Refresh'; btn.disabled = false; } }, 1000);
}

function startBriefRefresh() {
    if (briefRefreshTimer) clearInterval(briefRefreshTimer);
    prefetchBriefs();
    briefRefreshTimer = setInterval(() => {
        if (typeof activeTab !== 'undefined' && activeTab === 'brief') {
            loadBrief(activeBrief);
        }
    }, 60000);
}

function stopBriefRefresh() {
    if (briefRefreshTimer) {
        clearInterval(briefRefreshTimer);
        briefRefreshTimer = null;
    }
}

// --- EPS Render ---
function renderEps(container, data) {
    const s = data.stats;
    const act = data.activities;
    const t1 = act.tier1.length, t2 = act.tier2.length, to = act.other.length;
    const totalAct = t1 + t2 + to;

    let html = '';

    // Stats bar
    html += `<div class="grid grid-cols-3 gap-2 mb-4">
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Pipeline</div>
            <div class="text-sm font-semibold text-white">${s.pipeline_deals} deals</div>
            <div class="text-xs text-gray-500">$${(s.pipeline_value/1000).toFixed(0)}k</div>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Won (week)</div>
            <div class="text-sm font-semibold text-green-400">${s.won_week}</div>
            <div class="text-xs text-gray-500">$${(s.won_value_week/1000).toFixed(0)}k</div>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Calls (yday)</div>
            <div class="text-sm font-semibold text-blue-400">${s.yesterday_total_calls}</div>
            <div class="text-xs text-gray-500">${s.yesterday_cold_calls} cold</div>
        </div>
    </div>`;

    // Activities
    html += `<div class="mb-4">
        <div class="text-xs text-gray-500 uppercase tracking-wider mb-2">Today's Activities (${totalAct})</div>`;

    if (totalAct === 0) {
        html += '<div class="text-sm text-gray-600 py-2">No activities scheduled</div>';
    } else {
        if (t1 > 0) {
            html += '<div class="text-xs text-amber-400 font-semibold mb-1">PRIORITY</div>';
            act.tier1.forEach(a => { html += renderActivity(a); });
        }
        if (t2 > 0) {
            html += '<div class="text-xs text-gray-400 font-semibold mt-2 mb-1">OPERATIONAL</div>';
            act.tier2.forEach(a => { html += renderActivity(a); });
        }
        if (to > 0) {
            html += '<div class="text-xs text-gray-500 font-semibold mt-2 mb-1">OTHER</div>';
            act.other.forEach(a => { html += renderActivity(a); });
        }
    }
    html += '</div>';

    // Allen's Plate
    if (data.allens_plate.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-2">Allen's Plate (${data.allens_plate.length})</div>`;
        data.allens_plate.forEach(item => { html += renderActionItem(item); });
        html += '</div>';
    }

    // AI Can Handle
    if (data.ai_can_handle.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-blue-400 uppercase tracking-wider mb-2">AI Can Handle (${data.ai_can_handle.length})</div>`;
        data.ai_can_handle.forEach(item => { html += renderActionItem(item, true); });
        html += '</div>';
    }

    // Stale
    if (data.stale_deals.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-gray-500 uppercase tracking-wider mb-2">Stale Deals (${data.stale_deals.length})</div>`;
        data.stale_deals.forEach(d => {
            html += `<div class="bg-gray-900 rounded-lg p-2.5 mb-1.5 text-sm">
                <span class="text-gray-300">${d.deal_title}</span>
                <span class="text-gray-600 text-xs ml-1">${d.pipeline} / ${d.stage} &middot; ${d.days_since_activity}d</span>
            </div>`;
        });
        html += '</div>';
    }

    html += `<div class="text-xs text-gray-600 text-center mt-4">Updated ${data.updated}</div>`;
    container.innerHTML = html;
}

function renderActivity(a) {
    const overdueTag = a.overdue ? '<span class="text-red-400 text-xs ml-1">OVERDUE</span>' : '';
    const doneClass = a.done ? 'opacity-50 line-through' : '';
    const time = a.due_time ? `<span class="text-gray-500 text-xs mr-1">${a.due_time}</span>` : '';
    const deal = a.deal_title ? `<span class="text-gray-500 text-xs">&middot; ${a.deal_title}</span>` : '';
    return `<div class="bg-gray-900 rounded-lg px-3 py-2 mb-1 ${doneClass}">
        ${time}<span class="text-sm font-medium text-gray-300">${a.label}</span> ${deal}${overdueTag}
        ${a.subject ? `<div class="text-xs text-gray-500 mt-0.5">${a.subject}</div>` : ''}
    </div>`;
}

function renderActionItem(item, isAi) {
    const colors = { URGENT: 'text-red-400', HIGH: 'text-orange-400', MEDIUM: 'text-yellow-400', LOW: 'text-gray-400' };
    const priorityColor = colors[item.priority] || 'text-gray-400';
    const person = item.person_name ? ` (${item.person_name})` : '';
    const value = item.value ? ` &middot; $${item.value.toLocaleString()}` : '';
    const action = item.recommended_action === 'email' ? 'Send email' :
                   item.recommended_action === 'call_then_email' ? 'Call, then email' :
                   item.recommended_action === 'urgent' ? 'Follow up NOW' : item.recommended_action;
    const border = isAi ? 'border-l-2 border-blue-500' : '';

    return `<div class="bg-gray-900 rounded-lg p-2.5 mb-1.5 ${border}">
        <div class="text-sm">
            <span class="${priorityColor} font-semibold text-xs mr-1">${item.priority}</span>
            <span class="text-gray-300">${item.deal_title}${person}</span>
        </div>
        <div class="text-xs text-gray-500 mt-0.5">${item.pipeline} / ${item.stage}${value} &middot; ${item.days_since_activity}d ago</div>
        <div class="text-xs text-blue-400 mt-0.5">${action}</div>
    </div>`;
}

// --- Personal Render (mirrors EPS layout) ---
function renderPersonal(container, data) {
    const s = data.stats;
    let html = '';

    // Stats bar
    html += `<div class="grid grid-cols-4 gap-2 mb-4">
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Total</div>
            <div class="text-sm font-semibold text-white">${s.total_leads}</div>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Hot</div>
            <div class="text-sm font-semibold text-green-400">${s.hot}</div>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Callbacks</div>
            <div class="text-sm font-semibold text-amber-400">${s.callbacks_due}</div>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 text-center">
            <div class="text-xs text-gray-500">Draft</div>
            <div class="text-sm font-semibold text-blue-400">${s.emails_to_draft}</div>
        </div>
    </div>`;

    // Hot Leads (Priority)
    if (data.hot_leads && data.hot_leads.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-green-400 uppercase tracking-wider font-semibold mb-2">Hot Leads (${data.hot_leads.length})</div>`;
        data.hot_leads.forEach(l => { html += renderLeadItem(l, 'green'); });
        html += '</div>';
    }

    // Callbacks Due
    if (data.callbacks_due && data.callbacks_due.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-amber-400 uppercase tracking-wider font-semibold mb-2">Callbacks Due (${data.callbacks_due.length})</div>`;
        data.callbacks_due.forEach(l => { html += renderLeadItem(l, 'amber'); });
        html += '</div>';
    }

    // Emails to Draft
    if (data.emails_to_draft && data.emails_to_draft.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-blue-400 uppercase tracking-wider font-semibold mb-2">Emails Ready to Draft (${data.emails_to_draft.length})</div>`;
        data.emails_to_draft.forEach(l => {
            html += `<div class="bg-gray-900 rounded-lg p-2.5 mb-1.5 border-l-2 border-blue-500">
                <div class="text-sm">
                    <span class="text-gray-300">${l.business_name}</span>
                    ${l.decision_maker ? `<span class="text-gray-500 text-xs ml-1">(${l.decision_maker})</span>` : ''}
                </div>
                <div class="text-xs text-gray-500 mt-0.5">${l.group} &middot; Called ${l.date_called || '?'}</div>
                ${l.email ? `<div class="text-xs text-blue-400 mt-0.5">${l.email}</div>` : '<div class="text-xs text-red-400 mt-0.5">No email on file</div>'}
                ${l.notes ? `<div class="text-xs text-gray-600 mt-0.5 truncate">${l.notes}</div>` : ''}
            </div>`;
        });
        html += '</div>';
    }

    // Follow Ups
    if (data.follow_ups && data.follow_ups.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-2">Follow Ups (${data.follow_ups.length})</div>`;
        data.follow_ups.forEach(l => { html += renderLeadItem(l, 'gray'); });
        html += '</div>';
    }

    // Retry (No Answer 1-2)
    if (data.no_answers && data.no_answers.length > 0) {
        html += `<div class="mb-4">
            <div class="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Retry Queue (${data.no_answers.length})</div>`;
        data.no_answers.forEach(l => { html += renderLeadItem(l, 'gray'); });
        html += '</div>';
    }

    html += `<div class="text-xs text-gray-600 text-center mt-4">Updated ${data.updated}</div>`;
    container.innerHTML = html;
}

function renderLeadItem(l, color) {
    const colors = { URGENT: 'text-red-400', HIGH: 'text-orange-400', MEDIUM: 'text-yellow-400', LOW: 'text-gray-400' };
    const priorityColor = colors[l.priority] || 'text-gray-400';
    const overdueTag = l.overdue ? '<span class="text-red-400 text-xs ml-1">OVERDUE</span>' : '';
    const followUp = l.follow_up_date ? `<span class="text-xs text-gray-500">F/U: ${l.follow_up_date}</span>` : '';
    return `<div class="bg-gray-900 rounded-lg p-2.5 mb-1.5">
        <div class="text-sm">
            <span class="${priorityColor} font-semibold text-xs mr-1">${l.priority}</span>
            <span class="text-gray-300">${l.business_name}</span>
            ${l.decision_maker ? `<span class="text-gray-500 text-xs ml-1">(${l.decision_maker})</span>` : ''}
            ${overdueTag}
        </div>
        <div class="text-xs text-gray-500 mt-0.5">${l.group} &middot; ${l.call_outcome} &middot; ${l.date_called || 'Not called'} ${followUp ? '&middot; ' + followUp : ''}</div>
        ${l.notes ? `<div class="text-xs text-gray-600 mt-0.5 truncate">${l.notes}</div>` : ''}
    </div>`;
}

// --- AI Learning Render ---
function renderLearning(container, data) {
    const lesson = data.lesson;
    const summaries = data.summaries || {};
    let html = '';

    // Lesson header with Next button
    html += `<div class="bg-gray-900 rounded-xl p-4 mb-4 border-l-2 border-green-500">
        <div class="flex items-start justify-between">
            <div>
                <div class="text-xs text-green-400 font-semibold mb-1">${lesson.week_label || ''}</div>
                <div class="text-lg font-bold text-white mb-1">${lesson.title}</div>
                <div class="text-xs text-gray-500">${lesson.progress || ''}</div>
            </div>
            <button onclick="nextLesson()" id="next-lesson-btn"
                    class="px-3 py-1.5 text-xs font-medium bg-green-600 hover:bg-green-500 text-white rounded-lg transition shrink-0 ml-3">
                Next Lesson
            </button>
        </div>
    </div>`;

    // Articles with inline summaries (pre-cached)
    if (lesson.articles && lesson.articles.length > 0) {
        html += '<div class="text-xs text-gray-400 uppercase tracking-wider mb-2">Articles</div>';
        lesson.articles.forEach((a, idx) => {
            const summary = summaries[a.url];
            html += `<div class="mb-3">
                <a href="${a.url}" target="_blank" class="block bg-gray-900 rounded-lg p-3 hover:border-gray-700 border border-gray-800 transition">
                    <div class="text-base text-blue-400 font-medium">${a.title}</div>
                    <div class="text-sm text-gray-500 mt-1">${a.snippet}</div>
                </a>
                <div id="learn-summary-${idx}" class="px-3 py-2 text-sm text-gray-400">
                    ${summary ? formatSummary(summary) : '<span class="animate-pulse text-xs text-gray-500">Loading summary...</span>'}
                </div>
            </div>`;
        });
    }

    // Expert digest
    if (data.experts && data.experts.length > 0) {
        html += '<div class="text-xs text-gray-400 uppercase tracking-wider mt-4 mb-2">Expert Digest</div>';
        data.experts.forEach(expert => {
            html += `<div class="bg-gray-900 rounded-lg p-3 mb-1.5">
                <div class="text-sm font-semibold text-green-400 mb-1">${expert.name}</div>`;
            if (expert.articles && expert.articles.length > 0) {
                expert.articles.forEach(a => {
                    html += `<a href="${a.url}" target="_blank" class="block text-xs text-gray-400 hover:text-blue-400 mt-1">${a.title}</a>`;
                });
            } else {
                html += '<div class="text-xs text-gray-600">No updates</div>';
            }
            html += '</div>';
        });
    }

    html += `<div class="text-xs text-gray-600 text-center mt-4">Updated ${data.updated}</div>`;
    container.innerHTML = html;

    // Only fetch summaries that weren't pre-cached
    if (lesson.articles) {
        lesson.articles.forEach((a, idx) => {
            if (!summaries[a.url]) {
                fetchSummary(a.url, a.title, idx);
            }
        });
    }
}

function formatSummary(text) {
    const lines = text.split('\n').filter(l => l.trim());
    let html = '<div class="space-y-1 mt-1">';
    lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed === 'BULLETS:' || trimmed === 'ACTION:') {
            const label = trimmed.replace(':', '');
            html += `<div class="text-xs font-semibold text-gray-300 mt-2">${label}</div>`;
        } else if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
            html += `<div class="text-sm text-gray-400 pl-2">${trimmed}</div>`;
        }
    });
    html += '</div>';
    return html;
}

async function nextLesson() {
    const btn = document.getElementById('next-lesson-btn');
    if (btn) { btn.textContent = 'Generating...'; btn.disabled = true; }

    try {
        const res = await fetch('/api/learn/next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        const data = await res.json();
        if (data.ok) {
            // Poll until new lesson is ready (background generation)
            let attempts = 0;
            const poll = setInterval(async () => {
                attempts++;
                try {
                    const r = await fetch('/api/brief/learning');
                    const d = await r.json();
                    if (d.ok && d.lesson && d.lesson.progress !== briefCache['learning']?.lesson?.progress) {
                        clearInterval(poll);
                        briefCache['learning'] = d;
                        const container = document.getElementById('brief-learning');
                        if (container) renderLearning(container, d);
                        if (btn) { btn.textContent = 'Next Lesson'; btn.disabled = false; }
                    }
                } catch {}
                if (attempts > 30) {
                    clearInterval(poll);
                    if (btn) { btn.textContent = 'Next Lesson'; btn.disabled = false; }
                }
            }, 2000);
        }
    } catch {
        if (btn) { btn.textContent = 'Next Lesson'; btn.disabled = false; }
    }
}

async function fetchSummary(url, title, idx) {
    try {
        const res = await fetch('/api/learn/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, title }),
        });
        const data = await res.json();
        const el = document.getElementById(`learn-summary-${idx}`);
        if (!el) return;

        if (data.ok && data.summary) {
            el.innerHTML = formatSummary(data.summary);
        } else {
            el.innerHTML = '';
        }
    } catch {
        const el = document.getElementById(`learn-summary-${idx}`);
        if (el) el.innerHTML = '';
    }
}
