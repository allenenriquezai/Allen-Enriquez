// Today tab — queue / goals / journal

// Minimal markdown renderer: bold, headings, bullets, paragraphs.
function renderMiniMarkdown(raw) {
    if (!raw) return '<div class="text-gray-500 italic">Nothing here yet.</div>';
    const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const lines = raw.split('\n');
    let html = '';
    let inList = false;
    for (let line of lines) {
        const t = line.trim();
        if (!t) {
            if (inList) { html += '</ul>'; inList = false; }
            continue;
        }
        if (t.startsWith('### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h3 class="text-sm font-semibold text-gray-200 mt-3 mb-1">${esc(t.slice(4))}</h3>`;
        } else if (t.startsWith('## ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h2 class="text-base font-semibold text-white mt-4 mb-2">${esc(t.slice(3))}</h2>`;
        } else if (t.startsWith('# ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h1 class="text-lg font-bold text-white mt-4 mb-2">${esc(t.slice(2))}</h1>`;
        } else if (t.startsWith('- ') || t.startsWith('* ')) {
            if (!inList) { html += '<ul class="list-disc list-inside space-y-1 ml-1">'; inList = true; }
            let body = esc(t.slice(2)).replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>');
            html += `<li>${body}</li>`;
        } else {
            if (inList) { html += '</ul>'; inList = false; }
            let body = esc(t).replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>');
            html += `<p class="mb-2">${body}</p>`;
        }
    }
    if (inList) html += '</ul>';
    return html;
}

function relativeTime(iso) {
    if (!iso) return 'never';
    try {
        const then = new Date(iso).getTime();
        const diff = Math.floor((Date.now() - then) / 1000);
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
        return `${Math.floor(diff/86400)}d ago`;
    } catch { return iso; }
}

async function loadTodayQueue() {
    const list = document.getElementById('today-queue-list');
    const counts = document.getElementById('today-queue-counts');
    if (!list) return;
    list.innerHTML = '<div class="text-gray-400 italic text-center py-8 text-sm">Loading...</div>';
    try {
        const res = await fetch('/api/today/queue');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Queue failed');
        const items = data.items || [];
        if (counts && data.counts) {
            const parts = Object.entries(data.counts).map(([k, v]) => `${k}: ${v}`).join(' · ');
            counts.textContent = parts;
        }
        if (!items.length) {
            list.innerHTML = '<div class="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center text-sm text-gray-400">Queue clear. Nice.</div>';
            return;
        }
        list.innerHTML = items.map(it => {
            const icon = it.icon || '·';
            const domain = it.domain ? `<span class="text-[10px] uppercase tracking-wider text-gray-500 mr-2">${it.domain}</span>` : '';
            return `<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start gap-3">
                <div class="text-xl min-w-[24px] text-center">${icon}</div>
                <div class="flex-1 min-w-0 cursor-pointer" onclick="queueGoTo('${(it.cta||'').replace(/'/g, "\\'")}')">
                    <div>${domain}<span class="text-sm font-semibold text-gray-100">${escapeHtml(it.title||'')}</span></div>
                    <div class="text-xs text-gray-400 mt-1">${escapeHtml(it.context||'')}</div>
                </div>
                <button onclick="queueMarkDone('${(it.id||'').replace(/'/g, "\\'")}', this)"
                        class="px-3 py-2 bg-emerald-900/40 hover:bg-emerald-900/70 text-emerald-300 rounded-lg text-xs min-h-[44px]">Done</button>
            </div>`;
        }).join('');
    } catch (err) {
        list.innerHTML = `<div class="text-red-400 text-sm text-center py-6">${err.message}</div>`;
    }
}

function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function queueGoTo(cta) {
    if (!cta) return;
    const [tab, pill] = cta.split('#');
    if (tab) switchTab(tab);
    if (tab && pill) switchSubpill(tab, pill);
}

async function queueMarkDone(id, btn) {
    // Phase 1: just UI-log. Backend outcome log is Phase 2.
    if (btn) {
        btn.disabled = true;
        btn.textContent = '✓';
        btn.classList.add('opacity-60');
    }
    showToast('Logged');
}

async function loadTodayGoals() {
    const body = document.getElementById('today-goals-body');
    const meta = document.getElementById('today-goals-meta');
    if (!body) return;
    body.innerHTML = '<div class="text-gray-400 italic text-center py-6 text-sm">Loading...</div>';
    try {
        const res = await fetch('/api/today/goals');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Goals failed');
        body.innerHTML = data.exists ? renderMiniMarkdown(data.raw) : '<div class="text-gray-500 italic text-sm">No goals written yet. Tap Edit to start.</div>';
        if (meta) meta.textContent = data.last_modified ? `Updated ${relativeTime(data.last_modified)}` : '';
    } catch (err) {
        body.innerHTML = `<div class="text-red-400 text-sm">${err.message}</div>`;
    }
}

function openGoalsModal() {
    const modal = document.getElementById('goals-modal');
    const ta = document.getElementById('goals-textarea');
    if (!modal || !ta) return;
    ta.value = '';
    modal.classList.remove('hidden');
    fetch('/api/today/goals').then(r => r.json()).then(d => {
        if (d.ok && d.raw) ta.value = d.raw;
    });
}

function closeGoalsModal() {
    const modal = document.getElementById('goals-modal');
    if (modal) modal.classList.add('hidden');
}

async function saveGoals() {
    const ta = document.getElementById('goals-textarea');
    if (!ta) return;
    try {
        const res = await fetch('/api/today/goals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw: ta.value }),
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Save failed');
        closeGoalsModal();
        showToast('Saved', 'success');
        loadTodayGoals();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function todayDateStr() {
    const n = new Date();
    return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-${String(n.getDate()).padStart(2,'0')}`;
}

function parseJournalRaw(raw) {
    // Best-effort parse of the markdown journal we save (sections: Wins, Lesson, Tomorrow, Mood)
    const out = { wins: [], lesson: '', tomorrow: [], mood: '' };
    if (!raw) return out;
    const lines = raw.split('\n');
    let section = null;
    for (const line of lines) {
        const t = line.trim();
        if (/^##\s*Wins/i.test(t)) { section = 'wins'; continue; }
        if (/^##\s*Lesson/i.test(t)) { section = 'lesson'; continue; }
        if (/^##\s*Tomorrow/i.test(t)) { section = 'tomorrow'; continue; }
        if (/^##\s*Mood/i.test(t)) { section = 'mood'; continue; }
        if (!t) continue;
        if (section === 'wins' && (t.startsWith('- ') || t.startsWith('* '))) out.wins.push(t.slice(2));
        else if (section === 'tomorrow' && (t.startsWith('- ') || t.startsWith('* '))) out.tomorrow.push(t.slice(2));
        else if (section === 'lesson') out.lesson += (out.lesson ? '\n' : '') + t;
        else if (section === 'mood') {
            const m = t.match(/\d/);
            if (m) out.mood = m[0];
        }
    }
    return out;
}

let _selectedMood = '';

function setMood(val) {
    _selectedMood = String(val);
    document.querySelectorAll('#journal-mood .mood-btn').forEach(b => {
        if (b.dataset.mood === _selectedMood) {
            b.classList.remove('bg-gray-800', 'border-gray-700', 'text-gray-300');
            b.classList.add('bg-blue-600', 'border-blue-500', 'text-white');
        } else {
            b.classList.add('bg-gray-800', 'border-gray-700', 'text-gray-300');
            b.classList.remove('bg-blue-600', 'border-blue-500', 'text-white');
        }
    });
}

async function loadTodayJournal() {
    const yestBox = document.getElementById('today-journal-yesterday');
    if (yestBox) yestBox.innerHTML = '';

    // Wire mood buttons once
    document.querySelectorAll('#journal-mood .mood-btn').forEach(b => {
        if (!b.dataset.wired) {
            b.dataset.wired = '1';
            b.addEventListener('click', () => setMood(b.dataset.mood));
        }
    });

    try {
        const res = await fetch(`/api/today/journal?date=${todayDateStr()}`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Journal failed');

        if (data.yesterday && data.yesterday.exists && yestBox) {
            yestBox.innerHTML = `<div class="bg-gray-900/60 border border-gray-800 rounded-xl p-3">
                <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Yesterday — ${escapeHtml(data.yesterday.date||'')}</div>
                <div class="text-xs text-gray-400 whitespace-pre-wrap">${escapeHtml((data.yesterday.preview||'').slice(0, 280))}</div>
            </div>`;
        }

        if (data.exists && data.raw) {
            const parsed = parseJournalRaw(data.raw);
            const w = parsed.wins || [];
            document.getElementById('journal-win-1').value = w[0] || '';
            document.getElementById('journal-win-2').value = w[1] || '';
            document.getElementById('journal-win-3').value = w[2] || '';
            document.getElementById('journal-lesson').value = parsed.lesson || '';
            const t = parsed.tomorrow || [];
            document.getElementById('journal-tmr-1').value = t[0] || '';
            document.getElementById('journal-tmr-2').value = t[1] || '';
            document.getElementById('journal-tmr-3').value = t[2] || '';
            if (parsed.mood) setMood(parsed.mood);
        }
    } catch (err) {
        if (yestBox) yestBox.innerHTML = `<div class="text-red-400 text-xs">${err.message}</div>`;
    }
}

async function saveJournal() {
    const payload = {
        date: todayDateStr(),
        wins: [
            document.getElementById('journal-win-1').value.trim(),
            document.getElementById('journal-win-2').value.trim(),
            document.getElementById('journal-win-3').value.trim(),
        ],
        lesson: document.getElementById('journal-lesson').value.trim(),
        tomorrow: [
            document.getElementById('journal-tmr-1').value.trim(),
            document.getElementById('journal-tmr-2').value.trim(),
            document.getElementById('journal-tmr-3').value.trim(),
        ],
        mood: _selectedMood,
    };
    try {
        const res = await fetch('/api/today/journal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Save failed');
        showToast('Journal saved', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

window.loadTodayQueue = loadTodayQueue;
window.loadTodayGoals = loadTodayGoals;
window.loadTodayJournal = loadTodayJournal;
window.openGoalsModal = openGoalsModal;
window.closeGoalsModal = closeGoalsModal;
window.saveGoals = saveGoals;
window.saveJournal = saveJournal;
window.queueGoTo = queueGoTo;
window.queueMarkDone = queueMarkDone;
