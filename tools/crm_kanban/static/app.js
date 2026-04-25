// CRM Kanban Board — Frontend Logic

let currentCard = null; // Currently open modal card element
let isMoving = false;   // Lock to prevent double-drag duplicates

// --- SortableJS Init ---
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.kanban-column-body').forEach(col => {
        new Sortable(col, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'drag-ghost',
            dragClass: 'drag-active',
            delay: 50,
            delayOnTouchOnly: true,
            onStart: (evt) => {
                if (isMoving) { evt.cancel(); }
            },
            onEnd: handleDrop,
        });
    });
});

// Stage labels for toasts
const STAGE_NAMES = {
    call_queue: 'Call Queue',
    no_answer: 'No Answer',
    not_interested: 'Not Interested',
    callbacks: 'Callbacks',
    send_email: 'Send Email',
    awaiting_reply: 'Awaiting Reply',
    late_follow_up: 'Late Follow Up',
    warm_interest: 'Warm Interest',
    meeting_booked: 'Meeting Booked',
};

async function handleDrop(evt) {
    const card = evt.item;
    const sourceStage = evt.from.dataset.stage;
    const targetStage = evt.to.dataset.stage;

    if (sourceStage === targetStage) return;
    if (isMoving) {
        evt.from.insertBefore(card, evt.from.children[evt.oldIndex] || null);
        return;
    }

    isMoving = true;
    card.classList.add('opacity-50');
    document.querySelectorAll('.kanban-card').forEach(c => c.style.pointerEvents = 'none');

    try {
        const lead = JSON.parse(card.dataset.lead);
        const rowData = JSON.parse(card.dataset.rowData);
        const res = await fetch('/api/move-card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tab: lead.tab,
                row_num: lead.row_num,
                target_stage: targetStage,
                row_data: rowData,
                current_outcome: lead.call_outcome,
            }),
        });
        const data = await res.json();

        if (data.ok) {
            updateColumnCounts();
            showToast(`Moved to ${STAGE_NAMES[targetStage] || targetStage}`, 'success');
            setTimeout(() => location.reload(), 800);
        } else {
            evt.from.insertBefore(card, evt.from.children[evt.oldIndex] || null);
            showToast(`Move failed: ${data.error}`, 'error');
            isMoving = false;
            document.querySelectorAll('.kanban-card').forEach(c => c.style.pointerEvents = '');
        }
    } catch (err) {
        evt.from.insertBefore(card, evt.from.children[evt.oldIndex] || null);
        showToast('Network error', 'error');
        isMoving = false;
        document.querySelectorAll('.kanban-card').forEach(c => c.style.pointerEvents = '');
    }

    card.classList.remove('opacity-50');
}

// --- Column Counts ---
function updateColumnCounts() {
    document.querySelectorAll('.kanban-column').forEach(col => {
        const body = col.querySelector('.kanban-column-body');
        const badge = col.querySelector('.rounded-full');
        if (body && badge) {
            badge.textContent = body.children.length;
        }
    });
}

// --- Log Parsing ---
function parseLogEntries(notesText) {
    if (!notesText) return { calls: [], notes: [], legacy: '' };

    const calls = [], notes = [], legacyLines = [];
    const entryRe = /^\[(\d{1,2} \w+ \d{4} \d{2}:\d{2})\] \[(CALL|NOTE)\] (.+)$/;

    for (const line of notesText.split('\n')) {
        const m = line.trim().match(entryRe);
        if (m) {
            (m[2] === 'CALL' ? calls : notes).push({ ts: m[1], text: m[3] });
        } else if (line.trim()) {
            legacyLines.push(line.trim());
        }
    }

    return {
        calls: calls.reverse(),
        notes: notes.reverse(),
        legacy: legacyLines.join('\n'),
    };
}

function renderLogEntries(entries, legacy, containerEl) {
    let html = '';
    if (legacy) {
        html += `<div class="text-gray-400 bg-gray-800/50 rounded p-2 italic leading-relaxed">${escHtml(legacy)}</div>`;
    }
    for (const e of entries) {
        html += `<div class="flex gap-2 py-0.5 border-b border-gray-800/50 last:border-0">
            <span class="text-gray-600 shrink-0">${e.ts}</span>
            <span class="text-gray-200">${escHtml(e.text)}</span>
        </div>`;
    }
    containerEl.innerHTML = html || '<div class="text-gray-600 italic">No entries yet</div>';
}

function escHtml(text) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(text));
    return d.innerHTML;
}

function nowTs() {
    const n = new Date();
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const h = String(n.getHours()).padStart(2, '0');
    const m = String(n.getMinutes()).padStart(2, '0');
    return `${n.getDate()} ${months[n.getMonth()]} ${n.getFullYear()} ${h}:${m}`;
}

// --- Modal ---
function openModal(cardEl) {
    if (cardEl.classList.contains('drag-active')) return;

    currentCard = cardEl;
    const lead = JSON.parse(cardEl.dataset.lead);

    document.getElementById('modal-title').textContent = lead.business_name || '';

    const contactFields = {
        dm:      { value: lead.decision_maker || '', type: 'text' },
        phone:   { value: lead.phone || '',          type: 'tel' },
        phone2:  { value: lead.phone2 || '',         type: 'tel' },
        email:   { value: lead.email || '',          type: 'mailto' },
        website: { value: lead.website || '',        type: 'url' },
    };

    for (const [field, info] of Object.entries(contactFields)) {
        const input = document.getElementById(`modal-${field}`);
        const display = document.getElementById(`modal-${field}-display`);
        input.value = info.value;
        input.classList.add('hidden');
        display.classList.remove('hidden');

        if (info.value) {
            display.textContent = info.value;
            if (info.type === 'tel') display.href = `tel:${info.value}`;
            else if (info.type === 'mailto') display.href = `mailto:${info.value}`;
            else if (info.type === 'url') display.href = info.value.startsWith('http') ? info.value : `https://${info.value}`;
            else display.removeAttribute('href');
        } else {
            display.textContent = '-';
            display.removeAttribute('href');
        }
    }

    document.getElementById('modal-followup').value = lead.follow_up_date || '';
    document.getElementById('modal-outcome-new').value = lead.call_outcome || 'New / No Label';
    document.getElementById('modal-note-input').value = '';

    const parsed = parseLogEntries(lead.notes || '');
    renderLogEntries(parsed.calls, '', document.getElementById('modal-call-log'));
    renderLogEntries(parsed.notes, parsed.legacy, document.getElementById('modal-notes-log'));

    // Enrichment
    document.getElementById('modal-city').textContent = lead.city || '-';
    document.getElementById('modal-source').textContent = lead.source || '-';
    document.getElementById('modal-hook').textContent = lead.personal_hook || '-';
    document.getElementById('modal-called').textContent = lead.date_called || '-';
    document.getElementById('modal-bbb').textContent = lead.bbb_rating || '-';

    const liEl = document.getElementById('modal-linkedin');
    if (lead.linkedin) {
        liEl.innerHTML = `<a href="${lead.linkedin}" target="_blank" class="text-blue-400 hover:text-blue-300">${lead.linkedin}</a>`;
    } else {
        liEl.textContent = '-';
    }

    const socialEl = document.getElementById('modal-social');
    if (lead.social_media) {
        const links = lead.social_media.split('|').map(s => s.trim()).filter(Boolean);
        socialEl.innerHTML = links.map(url =>
            `<a href="${url}" target="_blank" class="text-blue-400 hover:text-blue-300 block truncate">${url}</a>`
        ).join('');
    } else {
        socialEl.textContent = '-';
    }

    document.getElementById('modal-overlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.body.style.overflow = '';
    currentCard = null;
}

async function saveCard() {
    if (!currentCard) return;

    const lead = JSON.parse(currentCard.dataset.lead);
    const updates = {};

    const fields = {
        'Decision Maker': [document.getElementById('modal-dm').value, lead.decision_maker || ''],
        'Phone':          [document.getElementById('modal-phone').value, lead.phone || ''],
        'Phone 2':        [document.getElementById('modal-phone2').value, lead.phone2 || ''],
        'Email':          [document.getElementById('modal-email').value, lead.email || ''],
        'Website':        [document.getElementById('modal-website').value, lead.website || ''],
        'Follow-up Date': [document.getElementById('modal-followup').value, lead.follow_up_date || ''],
    };
    for (const [key, [newVal, oldVal]] of Object.entries(fields)) {
        if (newVal !== oldVal) updates[key] = newVal;
    }

    if (Object.keys(updates).length === 0) {
        closeModal();
        return;
    }

    const btn = document.getElementById('modal-save-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/update-card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tab: lead.tab, row_num: lead.row_num, updates }),
        });
        const data = await res.json();

        if (data.ok) {
            showToast('Saved', 'success');
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(`Save failed: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }

    btn.textContent = 'Save';
    btn.disabled = false;
    closeModal();
}

// --- Log Call + optional Note ---
async function logCallAndNote() {
    if (!currentCard) return;
    const lead = JSON.parse(currentCard.dataset.lead);
    const outcome = document.getElementById('modal-outcome-new').value;
    if (!outcome) return;

    const ts = nowTs();
    const entries = [`[${ts}] [CALL] ${outcome}`];
    const noteText = document.getElementById('modal-note-input').value.trim();
    if (noteText) entries.push(`[${ts}] [NOTE] ${noteText}`);

    const btn = document.getElementById('log-call-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/append-log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tab: lead.tab, row_num: lead.row_num, entries, call_outcome: outcome }),
        });
        const data = await res.json();
        if (data.ok) {
            showToast('Logged', 'success');
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(`Error: ${data.error}`, 'error');
            btn.textContent = 'Log Call';
            btn.disabled = false;
        }
    } catch (err) {
        showToast('Network error', 'error');
        btn.textContent = 'Log Call';
        btn.disabled = false;
    }
}

// Close modal on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// --- Field display/edit toggle ---
function toggleFieldEdit(field) {
    const input = document.getElementById(`modal-${field}`);
    const display = document.getElementById(`modal-${field}-display`);

    if (input.classList.contains('hidden')) {
        display.classList.add('hidden');
        input.classList.remove('hidden');
        input.focus();
    } else {
        const val = input.value.trim();
        input.classList.add('hidden');
        display.classList.remove('hidden');

        if (val) {
            display.textContent = val;
            if (field === 'phone' || field === 'phone2') display.href = `tel:${val}`;
            else if (field === 'email') display.href = `mailto:${val}`;
            else if (field === 'website') display.href = val.startsWith('http') ? val : `https://${val}`;
        } else {
            display.textContent = '-';
            display.removeAttribute('href');
        }
    }
}

// --- Toast Notifications ---
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded-lg text-sm font-medium z-[60] transition-all transform
        ${type === 'success' ? 'bg-green-600 text-white' :
          type === 'error' ? 'bg-red-600 text-white' :
          'bg-gray-700 text-gray-200'}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// --- Call Stats Dashboard ---
function toggleStats() {
    const panel = document.getElementById('stats-panel');
    const main = document.getElementById('kanban-main');
    panel.classList.toggle('hidden');
    if (panel.classList.contains('hidden')) {
        main.style.height = 'calc(100vh - 57px)';
    } else {
        main.style.height = '';
    }
}

async function loadOutreachStats() {
    try {
        const res = await fetch('/api/outreach/detailed');
        const data = await res.json();
        if (!data.ok) return;

        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        const t = data.today;

        set('k-goal-num', t.total);
        set('k-goal-target', data.goal);
        const ring = document.getElementById('k-goal-ring');
        if (ring) {
            const pct = Math.min(t.total / data.goal, 1);
            ring.style.strokeDashoffset = 213.6 * (1 - pct);
            ring.style.stroke = pct >= 1 ? '#10b981' : pct >= 0.5 ? '#3b82f6' : '#ef4444';
        }

        set('k-convos', t.convos);
        set('k-no-answer', t.no_answer);
        set('k-hung-up', t.hung_up);
        set('k-warm', t.warm);
        set('k-conv-rate', t.conv_rate + '%');
        set('k-week-total', data.week.total);
        set('k-streak', data.streak + 'd');

        const chartEl = document.getElementById('k-trend');
        if (chartEl && data.trend) {
            const max = Math.max(...data.trend.map(d => d.calls), 1);
            chartEl.innerHTML = data.trend.map((d, i) => {
                const h = Math.max(d.calls / max * 100, 3);
                const isToday = i === data.trend.length - 1;
                const color = d.calls >= data.goal ? 'bg-emerald-500'
                           : d.calls >= data.goal * 0.5 ? 'bg-blue-500'
                           : d.calls > 0 ? 'bg-gray-600' : 'bg-gray-800';
                const ring = isToday ? 'ring-1 ring-white/40' : '';
                return `<div class="flex-1 ${color} ${ring} rounded-sm transition-all" style="height:${h}%" title="${d.date}: ${d.calls} calls"></div>`;
            }).join('');
        }

        const nudgesEl = document.getElementById('k-nudges');
        if (nudgesEl && data.nudges && data.nudges.length) {
            const colors = {
                action: 'border-blue-800/50 text-blue-300',
                push: 'border-amber-800/50 text-amber-300',
                warning: 'border-red-800/50 text-red-300',
                insight: 'border-cyan-800/50 text-cyan-300',
                win: 'border-emerald-800/50 text-emerald-300',
            };
            nudgesEl.innerHTML = data.nudges.map(n =>
                `<div class="flex-shrink-0 bg-gray-800 border ${colors[n.type] || ''} rounded-lg px-3 py-2 text-[11px] max-w-xs">${n.text}</div>`
            ).join('');
        }
    } catch (err) {
        console.error('Stats load failed:', err);
    }
}

document.addEventListener('DOMContentLoaded', loadOutreachStats);
