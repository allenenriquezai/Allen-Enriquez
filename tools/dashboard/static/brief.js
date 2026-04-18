// Enriquez OS — Brief tab JS
// Sub-nav pills: EPS / Personal / AI Learning
// Auto-refreshes every 60s

let briefRefreshTimer = null;
let briefCache = {};

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
    // Force clear cache and re-fetch the section currently visible on the Work tab
    const btn = document.getElementById('brief-refresh-btn');
    if (btn) { btn.textContent = '...'; btn.disabled = true; }
    const pill = (typeof activeSubpill !== 'undefined' && activeSubpill.work) || 'eps';
    const section = pill === 'brand' ? 'personal' : 'eps';
    briefCache[section] = null;
    loadBrief(section);
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

// Alias used by the Learn tab header refresh button
function refreshLearn() {
    refreshLearning();
}

function startBriefRefresh() {
    if (briefRefreshTimer) clearInterval(briefRefreshTimer);
    prefetchBriefs();
    briefRefreshTimer = setInterval(() => {
        if (typeof activeTab !== 'undefined' && activeTab === 'work') {
            const pill = (typeof activeSubpill !== 'undefined' && activeSubpill.work) || 'eps';
            const section = pill === 'brand' ? 'personal' : 'eps';
            loadBrief(section);
        }
    }, 60000);
}

function stopBriefRefresh() {
    if (briefRefreshTimer) {
        clearInterval(briefRefreshTimer);
        briefRefreshTimer = null;
    }
}

// --- Format dollar values (smart K/M) ---
function formatValue(val) {
    if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `$${(val / 1000).toFixed(0)}K`;
    return `$${val}`;
}

// --- EPS Render ---
function renderEps(container, data) {
    const s = data.stats;
    const act = data.activities;

    // Merge into two lists: Your Focus vs AI Is Handling
    const yourFocus = [];
    const aiHandling = [];

    // Exec activities (tier1) → Your Focus
    act.tier1.forEach(a => yourFocus.push({ type: 'activity', data: a }));
    // Action items needing Allen → Your Focus
    data.allens_plate.forEach(item => yourFocus.push({ type: 'action', data: item }));

    // Operational activities (tier2) + other → AI Is Handling
    act.tier2.forEach(a => aiHandling.push({ type: 'activity', data: a }));
    act.other.forEach(a => aiHandling.push({ type: 'activity', data: a }));
    // Auto-chase follow-ups → AI Is Handling
    data.ai_can_handle.forEach(item => aiHandling.push({ type: 'action', data: item }));

    let html = '';

    // Hero stat cards — bigger numbers, colored tints
    html += `<div class="grid grid-cols-2 gap-3 mb-4">
        <div class="bg-blue-950/50 rounded-xl p-4 text-center border border-gray-800/50">
            <div class="text-xs text-gray-500 mb-1">Pipeline</div>
            <div class="text-2xl font-bold text-white">${s.pipeline_deals} deals</div>
            <div class="text-sm text-gray-400">${formatValue(s.pipeline_value)}</div>
        </div>
        <div class="bg-purple-950/50 rounded-xl p-4 text-center border border-gray-800/50">
            <div class="text-xs text-gray-500 mb-1">Calls</div>
            <div class="text-2xl font-bold text-blue-400">${s.calls_this_week || 0}</div>
            <div class="text-sm text-gray-400">this week</div>
        </div>
    </div>`;

    // Progress bar + split count (gamification)
    const totalTasks = yourFocus.length + aiHandling.length;
    const doneTasks = [...act.tier1, ...act.tier2, ...act.other].filter(a => a.done).length;
    const pctDone = totalTasks > 0 ? Math.round(doneTasks / totalTasks * 100) : 0;
    const pctColor = pctDone >= 80 ? 'bg-green-500' : (pctDone >= 40 ? 'bg-amber-500' : 'bg-red-500');
    const pctTextColor = pctDone >= 80 ? 'text-green-400' : (pctDone >= 40 ? 'text-amber-400' : 'text-red-400');

    html += `<div class="mb-4">
        <div class="flex items-center justify-between mb-1.5">
            <div class="flex gap-3 text-xs">
                <span class="px-2 py-1 rounded-full bg-amber-500/10 text-amber-400">You: ${yourFocus.length}</span>
                <span class="px-2 py-1 rounded-full bg-blue-500/10 text-blue-400">AI: ${aiHandling.length}</span>
            </div>
            <span id="eps-progress-pct" class="text-sm font-bold ${pctTextColor}">${pctDone}%</span>
        </div>
        <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div id="eps-progress-bar" class="h-full ${pctColor} rounded-full transition-all duration-700 ease-out" style="width: ${pctDone}%"></div>
        </div>
    </div>`;

    // Your Focus — amber dot header
    html += `<div class="mb-5">
        <div class="text-sm font-medium text-gray-300 mb-3"><span class="inline-block w-2 h-2 rounded-full bg-amber-500 mr-2"></span>Your Focus (${yourFocus.length})</div>`;
    if (yourFocus.length === 0) {
        html += '<div class="text-base text-gray-600 py-3">Nothing needs your attention</div>';
    } else {
        yourFocus.forEach(item => {
            if (item.type === 'activity') html += renderActivity(item.data, 'focus');
            else html += renderActionItem(item.data, false);
        });
    }
    html += '</div>';

    // AI Is Handling — blue dot header
    html += `<div class="mb-5">
        <div class="text-sm font-medium text-gray-300 mb-3"><span class="inline-block w-2 h-2 rounded-full bg-blue-500 mr-2"></span>AI Is Handling (${aiHandling.length})</div>`;
    if (aiHandling.length === 0) {
        html += '<div class="text-base text-gray-600 py-3">Nothing in the AI queue</div>';
    } else {
        aiHandling.forEach(item => {
            if (item.type === 'activity') html += renderActivity(item.data, 'ai');
            else html += renderActionItem(item.data, true);
        });
    }
    html += '</div>';

    // Going Cold — gray dot header
    if (data.stale_deals.length > 0) {
        html += `<div class="mb-5">
            <div class="text-sm font-medium text-gray-300 mb-3"><span class="inline-block w-2 h-2 rounded-full bg-gray-500 mr-2"></span>Going Cold (${data.stale_deals.length})</div>`;
        data.stale_deals.forEach(d => {
            const dealLink = d.deal_id
                ? `<span class="text-gray-200 cursor-pointer hover:text-blue-400 transition" onclick="event.stopPropagation();openDealPanel(${d.deal_id})">${d.deal_title}</span>`
                : `<span class="text-gray-200">${d.deal_title}</span>`;
            html += `<div class="bg-gray-900 rounded-xl px-3 py-2.5 mb-1 hover:bg-gray-800/50 transition">
                ${dealLink}
                <span class="text-gray-500 text-sm ml-2">${d.pipeline} / ${d.stage} &middot; ${d.days_since_activity}d</span>
            </div>`;
        });
        html += '</div>';
    }

    html += `<div class="text-sm text-gray-600 text-center mt-5">Updated ${data.updated}</div>`;
    container.innerHTML = html;
}

function renderActivity(a, section) {
    const overdueTag = a.overdue ? '<span class="text-red-400 text-xs ml-1 font-semibold">OVERDUE</span>' : '';
    const doneClass = a.done ? 'opacity-50 line-through' : '';
    const time = a.due_time ? `<span class="text-gray-500 text-sm mr-2">${a.due_time}</span>` : '';

    // Clickable deal name
    const dealLink = a.deal_title
        ? (a.deal_id
            ? `<span class="text-gray-400 text-sm cursor-pointer hover:text-blue-400 transition" onclick="event.stopPropagation();openDealPanel(${a.deal_id})">&middot; ${a.deal_title}</span>`
            : `<span class="text-gray-500 text-sm">&middot; ${a.deal_title}</span>`)
        : '';

    // Section-based styling
    const sectionBorder = section === 'focus' ? 'border-l-2 border-l-amber-500' : (section === 'ai' ? 'border-l-2 border-l-blue-500 opacity-80' : '');

    // Checkbox
    const actId = a.id || '';
    const checkboxFilled = a.done
        ? '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>'
        : '';
    const checkboxClasses = a.done
        ? 'w-5 h-5 rounded-full border-2 border-green-500 bg-green-500 flex items-center justify-center cursor-pointer shrink-0 transition'
        : 'w-5 h-5 rounded-full border-2 border-gray-600 flex items-center justify-center cursor-pointer shrink-0 hover:border-green-500 transition';

    return `<div class="bg-gray-900 rounded-xl px-3 py-2.5 mb-1 ${sectionBorder} ${doneClass} hover:bg-gray-800/50 transition">
        <div class="flex items-start gap-2.5">
            <div class="${checkboxClasses}" onclick="event.stopPropagation();toggleTaskDone(${actId ? actId : "''"}, this)">${checkboxFilled}</div>
            <div class="flex-1 min-w-0">
                ${time}<span class="text-base font-medium text-gray-200">${a.label}</span> ${dealLink}${overdueTag}
                ${a.subject ? `<div class="text-sm text-gray-500 mt-1">${a.subject}</div>` : ''}
            </div>
        </div>
    </div>`;
}

function renderActionItem(item, isAi) {
    const colors = { URGENT: 'text-red-400', HIGH: 'text-orange-400', MEDIUM: 'text-yellow-400', LOW: 'text-gray-400' };
    const priorityColor = colors[item.priority] || 'text-gray-400';
    const person = item.person_name ? ` (${item.person_name})` : '';
    const value = item.value ? ` &middot; ${formatValue(item.value)}` : '';
    const action = item.recommended_action === 'email' ? 'Send email' :
                   item.recommended_action === 'call_then_email' ? 'Call, then email' :
                   item.recommended_action === 'urgent' ? 'Follow up NOW' : item.recommended_action;

    // Section-based styling
    const sectionBorder = isAi ? 'border-l-2 border-l-blue-500 opacity-80' : 'border-l-2 border-l-amber-500';

    // Clickable deal name
    const dealTitleHtml = item.deal_id
        ? `<span class="text-gray-200 cursor-pointer hover:text-blue-400 transition" onclick="event.stopPropagation();openDealPanel(${item.deal_id})">${item.deal_title}</span>`
        : `<span class="text-gray-200">${item.deal_title}</span>`;

    // Checkbox (visual only for action items — no activity_id)
    const checkboxClasses = 'w-5 h-5 rounded-full border-2 border-gray-600 flex items-center justify-center cursor-pointer shrink-0 hover:border-green-500 transition';

    return `<div class="bg-gray-900 rounded-xl px-3 py-2.5 mb-1 ${sectionBorder} hover:bg-gray-800/50 transition">
        <div class="flex items-start gap-2.5">
            <div class="${checkboxClasses}" onclick="event.stopPropagation();toggleTaskDone('', this)"></div>
            <div class="flex-1 min-w-0">
                <div class="text-base">
                    <span class="${priorityColor} font-semibold text-xs mr-1">${item.priority}</span>
                    ${dealTitleHtml}${person}
                </div>
                <div class="text-sm text-gray-500 mt-1">${item.pipeline} / ${item.stage}${value} &middot; ${item.days_since_activity}d ago</div>
                <div class="text-sm text-blue-400 mt-1">${action}</div>
            </div>
        </div>
    </div>`;
}

// --- Task checkbox toggle ---
function toggleTaskDone(activityId, el) {
    // Visual toggle
    const row = el.closest('.bg-gray-900');
    const isDone = el.classList.contains('bg-green-500');

    if (isDone) {
        // Undo visual
        el.classList.remove('bg-green-500', 'border-green-500');
        el.classList.add('border-gray-600');
        el.innerHTML = '';
        if (row) {
            row.classList.remove('opacity-50', 'line-through');
        }
    } else {
        // Mark done visual
        el.classList.add('bg-green-500', 'border-green-500');
        el.classList.remove('border-gray-600');
        el.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
        if (row) {
            row.classList.add('opacity-50', 'line-through');
        }

        // POST to backend if we have an activity ID
        if (activityId && activityId !== '') {
            fetch(`/api/activity/${activityId}/done`, { method: 'POST' })
                .catch(() => {});
        }
    }

    // Update progress bar
    updateEpsProgress();
}

function updateEpsProgress() {
    const container = document.getElementById('brief-eps');
    if (!container) return;
    const allCheckboxes = container.querySelectorAll('.rounded-full.border-2');
    const total = allCheckboxes.length;
    const done = container.querySelectorAll('.rounded-full.border-2.bg-green-500').length;
    const pct = total > 0 ? Math.round(done / total * 100) : 0;

    const bar = document.getElementById('eps-progress-bar');
    const label = document.getElementById('eps-progress-pct');
    if (bar) {
        bar.style.width = `${pct}%`;
        bar.className = `h-full rounded-full transition-all duration-700 ease-out ${pct >= 80 ? 'bg-green-500' : (pct >= 40 ? 'bg-amber-500' : 'bg-red-500')}`;
    }
    if (label) {
        label.textContent = `${pct}%`;
        label.className = `text-sm font-bold ${pct >= 80 ? 'text-green-400' : (pct >= 40 ? 'text-amber-400' : 'text-red-400')}`;
    }
}

// --- Deal context panel ---
function openDealPanel(dealId) {
    const panel = document.getElementById('deal-panel');
    const title = document.getElementById('deal-panel-title');
    const content = document.getElementById('deal-panel-content');

    if (!panel) return;
    panel.classList.remove('hidden');
    title.textContent = 'Loading...';
    content.innerHTML = '<div class="text-gray-500 text-center py-4 text-sm loading-pulse">Loading deal context...</div>';

    fetch(`/api/deal/${dealId}/context`)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                content.innerHTML = `<div class="text-red-400 text-center py-4 text-sm">Error: ${data.error}</div>`;
                return;
            }
            const d = data.deal;
            title.textContent = d.title;

            let html = '';

            // Contact info bar
            html += '<div class="bg-gray-800 rounded-xl p-3 mb-3">';
            if (d.person_name) html += `<div class="text-sm text-gray-200 font-medium">${d.person_name}</div>`;
            if (d.org_name) html += `<div class="text-xs text-gray-400">${d.org_name}</div>`;
            const contactLinks = [];
            if (d.person_phone) contactLinks.push(`<a href="tel:${d.person_phone}" class="text-blue-400 hover:text-blue-300 transition">${d.person_phone}</a>`);
            if (d.person_email) contactLinks.push(`<a href="mailto:${d.person_email}" class="text-blue-400 hover:text-blue-300 transition text-xs">${d.person_email}</a>`);
            if (contactLinks.length) html += `<div class="text-sm mt-1 flex flex-wrap gap-3">${contactLinks.join('')}</div>`;
            html += '</div>';

            // Deal info
            html += `<div class="flex flex-wrap gap-2 mb-3 text-xs">
                <span class="px-2 py-1 rounded-full bg-gray-800 text-gray-300">${d.pipeline}</span>
                <span class="px-2 py-1 rounded-full bg-gray-800 text-gray-300">${d.stage}</span>
                ${d.value ? `<span class="px-2 py-1 rounded-full bg-green-900/50 text-green-400">${formatValue(d.value)}</span>` : ''}
            </div>`;

            // Recent activities
            if (data.activities && data.activities.length > 0) {
                html += '<div class="mb-3"><div class="text-xs text-gray-500 mb-2">Recent Activities</div>';
                data.activities.slice(0, 10).forEach(act => {
                    const doneIcon = act.done
                        ? '<span class="text-green-500 shrink-0">&#10003;</span>'
                        : '<span class="text-gray-600 shrink-0">&#9675;</span>';
                    html += `<div class="flex items-start gap-2 py-1.5 border-b border-gray-800/50 text-sm">
                        ${doneIcon}
                        <div class="flex-1 min-w-0">
                            <span class="text-gray-300">${act.subject || act.type}</span>
                            ${act.note ? `<div class="text-xs text-gray-500 mt-0.5 truncate">${act.note}</div>` : ''}
                        </div>
                        <span class="text-xs text-gray-600 shrink-0">${act.due_date}</span>
                    </div>`;
                });
                html += '</div>';
            }

            // Notes
            if (data.notes && data.notes.length > 0) {
                html += '<div class="mb-3"><div class="text-xs text-gray-500 mb-2">Notes</div>';
                data.notes.slice(0, 5).forEach(n => {
                    html += `<div class="py-1.5 border-b border-gray-800/50 text-sm">
                        <div class="text-gray-300">${n.content}</div>
                        <div class="text-xs text-gray-600 mt-0.5">${n.add_time ? n.add_time.slice(0, 10) : ''}</div>
                    </div>`;
                });
                html += '</div>';
            }

            // Add note input
            html += `<div class="mt-3">
                <div class="flex gap-2">
                    <input id="deal-note-input" type="text" placeholder="Add a note..."
                        class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:border-blue-500 outline-none"
                        onkeydown="if(event.key==='Enter'){event.preventDefault();addDealNote(${dealId})}">
                    <button onclick="addDealNote(${dealId})"
                        class="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition shrink-0">Add</button>
                </div>
            </div>`;

            content.innerHTML = html;
        })
        .catch(() => {
            content.innerHTML = '<div class="text-red-400 text-center py-4 text-sm">Failed to load deal</div>';
        });
}

function closeDealPanel() {
    const panel = document.getElementById('deal-panel');
    if (panel) panel.classList.add('hidden');
}

function addDealNote(dealId) {
    const input = document.getElementById('deal-note-input');
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;

    input.disabled = true;
    fetch(`/api/deal/${dealId}/note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            // Refresh the panel to show the new note
            openDealPanel(dealId);
        } else {
            input.disabled = false;
        }
    })
    .catch(() => { input.disabled = false; });
}

// --- Personal Render (mirrors EPS layout) ---
function renderPersonal(container, data) {
    const s = data.stats;
    let html = '';

    // Stats bar
    html += `<div class="grid grid-cols-4 gap-3 mb-5">
        <div class="bg-gray-900 rounded-xl p-4 text-center border border-gray-800">
            <div class="text-xs text-gray-500 mb-1">Total</div>
            <div class="text-lg font-bold text-white">${s.total_leads}</div>
        </div>
        <div class="bg-gray-900 rounded-xl p-4 text-center border border-gray-800">
            <div class="text-xs text-gray-500 mb-1">Hot</div>
            <div class="text-lg font-bold text-green-400">${s.hot}</div>
        </div>
        <div class="bg-gray-900 rounded-xl p-4 text-center border border-gray-800">
            <div class="text-xs text-gray-500 mb-1">Callbacks</div>
            <div class="text-lg font-bold text-amber-400">${s.callbacks_due}</div>
        </div>
        <div class="bg-gray-900 rounded-xl p-4 text-center border border-gray-800">
            <div class="text-xs text-gray-500 mb-1">Draft</div>
            <div class="text-lg font-bold text-blue-400">${s.emails_to_draft}</div>
        </div>
    </div>`;

    // Hot Leads (Priority)
    if (data.hot_leads && data.hot_leads.length > 0) {
        html += `<div class="mb-5">
            <div class="text-sm text-green-400 uppercase tracking-wider font-semibold mb-3">Hot Leads (${data.hot_leads.length})</div>`;
        data.hot_leads.forEach(l => { html += renderLeadItem(l, 'green'); });
        html += '</div>';
    }

    // Callbacks Due
    if (data.callbacks_due && data.callbacks_due.length > 0) {
        html += `<div class="mb-5">
            <div class="text-sm text-amber-400 uppercase tracking-wider font-semibold mb-3">Callbacks Due (${data.callbacks_due.length})</div>`;
        data.callbacks_due.forEach(l => { html += renderLeadItem(l, 'amber'); });
        html += '</div>';
    }

    // Emails to Draft
    if (data.emails_to_draft && data.emails_to_draft.length > 0) {
        html += `<div class="mb-5">
            <div class="text-sm text-blue-400 uppercase tracking-wider font-semibold mb-3">Emails Ready to Draft (${data.emails_to_draft.length})</div>`;
        data.emails_to_draft.forEach(l => {
            html += `<div class="bg-gray-900 rounded-xl px-4 py-3 mb-2 border border-gray-800 border-l-2 border-l-blue-500">
                <div class="text-base">
                    <span class="text-gray-200">${l.business_name}</span>
                    ${l.decision_maker ? `<span class="text-gray-500 text-sm ml-1">(${l.decision_maker})</span>` : ''}
                </div>
                <div class="text-sm text-gray-500 mt-1">${l.group} &middot; Called ${l.date_called || '?'}</div>
                ${l.email ? `<div class="text-sm text-blue-400 mt-1">${l.email}</div>` : '<div class="text-sm text-red-400 mt-1">No email on file</div>'}
                ${l.notes ? `<div class="text-sm text-gray-600 mt-1 truncate">${l.notes}</div>` : ''}
            </div>`;
        });
        html += '</div>';
    }

    // Follow Ups
    if (data.follow_ups && data.follow_ups.length > 0) {
        html += `<div class="mb-5">
            <div class="text-sm text-gray-400 uppercase tracking-wider font-semibold mb-3">Follow Ups (${data.follow_ups.length})</div>`;
        data.follow_ups.forEach(l => { html += renderLeadItem(l, 'gray'); });
        html += '</div>';
    }

    // Retry (No Answer 1-2)
    if (data.no_answers && data.no_answers.length > 0) {
        html += `<div class="mb-5">
            <div class="text-sm text-gray-500 uppercase tracking-wider font-semibold mb-3">Retry Queue (${data.no_answers.length})</div>`;
        data.no_answers.forEach(l => { html += renderLeadItem(l, 'gray'); });
        html += '</div>';
    }

    html += `<div class="text-sm text-gray-600 text-center mt-5">Updated ${data.updated}</div>`;
    container.innerHTML = html;
}

function renderLeadItem(l, color) {
    const colors = { URGENT: 'text-red-400', HIGH: 'text-orange-400', MEDIUM: 'text-yellow-400', LOW: 'text-gray-400' };
    const priorityColor = colors[l.priority] || 'text-gray-400';
    const overdueTag = l.overdue ? '<span class="text-red-400 text-xs ml-1 font-semibold">OVERDUE</span>' : '';
    const followUp = l.follow_up_date ? `<span class="text-sm text-gray-500">F/U: ${l.follow_up_date}</span>` : '';
    return `<div class="bg-gray-900 rounded-xl px-4 py-3 mb-2 border border-gray-800">
        <div class="text-base">
            <span class="${priorityColor} font-semibold text-xs mr-1">${l.priority}</span>
            <span class="text-gray-200">${l.business_name}</span>
            ${l.decision_maker ? `<span class="text-gray-500 text-sm ml-1">(${l.decision_maker})</span>` : ''}
            ${overdueTag}
        </div>
        <div class="text-sm text-gray-500 mt-1">${l.group} &middot; ${l.call_outcome} &middot; ${l.date_called || 'Not called'} ${followUp ? '&middot; ' + followUp : ''}</div>
        ${l.notes ? `<div class="text-sm text-gray-600 mt-1 truncate">${l.notes}</div>` : ''}
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
    let html = '<div class="space-y-2 mt-2">';
    lines.forEach(line => {
        const trimmed = line.trim();
        // Bold inline markers: **text** → <strong>
        const withBold = trimmed.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-200">$1</strong>');
        if (trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*')) {
            // Bullet point — strip leading marker
            const content = withBold.replace(/^[•\-*]\s*/, '');
            html += `<div class="text-sm text-gray-400 pl-3 flex gap-2"><span class="text-green-500 shrink-0">•</span><span>${content}</span></div>`;
        } else {
            // Paragraph text
            html += `<p class="text-sm text-gray-300 leading-relaxed">${withBold}</p>`;
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
