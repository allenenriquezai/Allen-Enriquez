// Enriquez OS Dashboard — Main JS

// Current date (YYYY-MM-DD)
let currentDate = new URLSearchParams(window.location.search).get('date')
    || (() => { const n = new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-${String(n.getDate()).padStart(2,'0')}`; })();

// Active tab + sub-pill state
let activeTab = 'today';
const activeSubpill = {
    today: 'queue',
    personal: 'habits',
    brand: 'content',
    eps: 'brief',
    vault: 'briefs',
};
// Inner tab state for Brand > Content (pipeline/buffer/published)
let activeContentTab = 'pipeline';

// --- Tab Navigation ---
function switchTab(tab) {
    activeTab = tab;

    // Hide all pages
    document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));

    // Show selected page
    const page = document.getElementById(`page-${tab}`);
    if (page) page.classList.remove('hidden');

    // Update tab button styles
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.dataset.tab === tab) {
            btn.classList.remove('text-gray-500');
            btn.classList.add('text-green-400');
        } else {
            btn.classList.remove('text-green-400');
            btn.classList.add('text-gray-500');
        }
    });

    // Lazy-load data when switching tabs (also fires the active sub-pill loader)
    runSubpillLoader(tab, activeSubpill[tab]);

    // Brief auto-refresh only when on Work tab
    if (tab === 'work') {
        if (typeof startBriefRefresh === 'function') startBriefRefresh();
    } else {
        if (typeof stopBriefRefresh === 'function') stopBriefRefresh();
    }

    // Scroll to top
    window.scrollTo(0, 0);
}

// --- Sub-pill switching ---
function switchSubpill(tab, pill) {
    activeSubpill[tab] = pill;

    // Update pill styles within this tab's page
    const page = document.getElementById(`page-${tab}`);
    if (!page) return;

    page.querySelectorAll('.subpill').forEach(btn => {
        if (btn.dataset.tab !== tab) return;
        if (btn.dataset.pill === pill) {
            btn.classList.remove('bg-gray-800', 'text-gray-400');
            btn.classList.add('bg-blue-600', 'text-white');
        } else {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('bg-gray-800', 'text-gray-400');
        }
    });

    // Hide all sub-pill containers within this tab, show the active one
    page.querySelectorAll('.subpill-content').forEach(el => el.classList.add('hidden'));
    const target = document.getElementById(`subpill-${tab}-${pill}`);
    if (target) target.classList.remove('hidden');

    runSubpillLoader(tab, pill);
}

// Map tab+pill -> data loader
function runSubpillLoader(tab, pill) {
    // Today tab (NEW default)
    if (tab === 'today' && pill === 'queue') {
        if (typeof loadTodayQueue === 'function') loadTodayQueue();
    }
    if (tab === 'today' && pill === 'goals') {
        if (typeof loadTodayGoals === 'function') loadTodayGoals();
    }
    if (tab === 'today' && pill === 'journal') {
        if (typeof loadTodayJournal === 'function') loadTodayJournal();
    }

    // Personal
    if (tab === 'personal' && pill === 'spend') {
        if (typeof loadSpend === 'function') loadSpend();
    }
    if (tab === 'personal' && pill === 'habits') {
        if (typeof loadCommandCenter === 'function') loadCommandCenter();
    }

    // Brand (was Work/Content/Outreach)
    if (tab === 'brand' && pill === 'content') {
        if (typeof loadContentOps === 'function') loadContentOps();
        if (typeof loadContentBank === 'function') loadContentBank();
    }
    if (tab === 'brand' && pill === 'outreach') {
        if (typeof loadOutreachHub === 'function') loadOutreachHub();
        else if (typeof loadOutreachOps === 'function') loadOutreachOps();
    }
    if (tab === 'brand' && pill === 'outcomes') {
        if (typeof loadOutcomes === 'function') loadOutcomes();
    }
    if (tab === 'brand' && pill === 'systems') {
        if (typeof loadSystems === 'function') loadSystems();
    }

    // EPS (was Work > EPS)
    if (tab === 'eps' && pill === 'brief') {
        if (typeof loadBrief === 'function') loadBrief('eps');
        if (typeof loadCommandCenter === 'function') loadCommandCenter();
    }
    if (tab === 'eps' && pill === 'calls') {
        if (typeof loadBrief === 'function') loadBrief('eps');
        if (typeof loadCommandCenter === 'function') loadCommandCenter();
    }

    // Vault (was Learn)
    if (tab === 'vault' && pill === 'briefs') {
        if (typeof loadLearning === 'function') loadLearning();
    }
    if (tab === 'vault' && pill === 'notes') {
        if (typeof loadLibrary === 'function') loadLibrary('notes');
    }
    if (tab === 'vault' && pill === 'projects') {
        if (typeof loadLibrary === 'function') loadLibrary('projects');
    }
    if (tab === 'vault' && pill === 'links') {
        if (typeof loadLibrary === 'function') loadLibrary('links');
    }
    if (tab === 'vault' && pill === 'files') {
        if (typeof loadFiles === 'function') loadFiles();
    }
    if (tab === 'vault' && pill === 'archive') {
        // Phase 3 — placeholder
    }
}

// --- Date Navigation (AJAX — no page reload) ---
async function changeDate(delta) {
    const d = new Date(currentDate + 'T12:00:00');
    d.setDate(d.getDate() + delta);
    currentDate = d.toISOString().slice(0, 10);

    // Update URL without reload
    history.pushState({date: currentDate}, '', `/?date=${currentDate}`);

    // Update all date displays
    updateDateDisplays();

    // Reload data for the active tab — rebuild sections if weekday/weekend changed
    try {
        const [configRes, logRes] = await Promise.all([
            fetch(`/api/checklist/config?date=${currentDate}`),
            fetch(`/api/checklist/${currentDate}`),
        ]);
        const configData = await configRes.json();
        const logData = await logRes.json();
        if (configData.ok && logData.ok) {
            rebuildHabitSections(configData.config, logData.completions);
        }
    } catch (err) {
        showToast('Failed to load habits', 'error');
    }

    // Also reload spend if that tab exists
    if (typeof loadSpend === 'function') loadSpend();
    // Reload command center stats
    if (typeof loadCommandCenter === 'function') loadCommandCenter();
}

function updateDateDisplays() {
    const d = new Date(currentDate + 'T12:00:00');
    const now = new Date();
    const today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    const formatted = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

    const display = document.getElementById('date-display');
    const label = document.getElementById('date-label');
    if (display) display.textContent = formatted;
    if (label) {
        if (currentDate === today) {
            label.textContent = 'Today';
            label.className = 'text-xs text-green-400';
        } else {
            label.textContent = currentDate;
            label.className = 'text-xs text-gray-400';
        }
    }

    const spendDate = document.getElementById('spend-date-display');
    if (spendDate) spendDate.textContent = formatted;
    const personalDate = document.getElementById('personal-date');
    if (personalDate) personalDate.textContent = formatted;
}

function updateChecklistUI(completions) {
    document.querySelectorAll('[data-item][data-type]').forEach(row => {
        const name = row.dataset.item;
        const type = row.dataset.type;
        const val = completions[name] || '';

        if (type === 'check') {
            const isDone = ['TRUE', '1', 'YES'].includes(val.toUpperCase());
            const checkbox = row.querySelector('.w-5.h-5');
            const label = row.querySelector('span.text-base');

            if (isDone) {
                checkbox.classList.add('bg-green-600', 'border-green-600');
                checkbox.classList.remove('border-gray-600');
                checkbox.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
                label.classList.add('line-through', 'text-gray-500');
                label.classList.remove('text-gray-200');
                row.classList.add('opacity-60');
            } else {
                checkbox.classList.remove('bg-green-600', 'border-green-600');
                checkbox.classList.add('border-gray-600');
                checkbox.innerHTML = '';
                label.classList.remove('line-through', 'text-gray-500');
                label.classList.add('text-gray-200');
                row.classList.remove('opacity-60');
            }
        } else {
            const input = row.querySelector('.count-input');
            const value = parseInt(val) || 0;
            if (input) input.value = value;
            if (value > 0) row.classList.add('opacity-60');
            else row.classList.remove('opacity-60');
        }
    });

    updateProgress();

    // Update category counters
    document.querySelectorAll('section.mb-4').forEach(section => {
        const items = section.querySelectorAll('[data-item][data-type]');
        let total = items.length, done = 0;
        items.forEach(item => {
            if (item.dataset.type === 'check') {
                if (item.querySelector('.bg-green-600')) done++;
            } else {
                const input = item.querySelector('.count-input');
                if (input && parseInt(input.value) > 0) done++;
            }
        });
        const counter = section.querySelector('.text-xs.text-gray-400');
        if (counter && counter.textContent.includes('/')) {
            counter.textContent = `${done}/${total}`;
        }
    });
}

// Rebuild habit sections from config + completions (handles weekday/weekend swap)
function rebuildHabitSections(config, completions) {
    const container = document.getElementById('section-habits');
    if (!container) return;

    const catOrder = ['Personal Morning', 'Personal Brand', 'EPS', 'Workout', 'Family & Home', 'Personal Closing'];
    let html = '';
    let totalItems = 0, totalDone = 0;

    for (const cat of catOrder) {
        const items = config[cat];
        if (!items || !items.length) continue;

        let catDone = 0;
        let itemsHtml = '';
        for (const item of items) {
            totalItems++;
            const val = completions[item.name] || '';
            let isDone = false;
            if (item.type === 'check') {
                isDone = ['TRUE', '1', 'YES'].includes(val.toUpperCase());
            } else {
                isDone = !!(val && val !== '0');
            }
            if (isDone) { catDone++; totalDone++; }

            if (item.type === 'check') {
                const doneClass = isDone ? 'opacity-60' : '';
                const cbClass = isDone ? 'bg-green-600 border-green-600' : 'border-gray-600';
                const checkSvg = isDone ? '<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>' : '';
                const labelClass = isDone ? 'line-through text-gray-500' : 'text-gray-200';
                itemsHtml += `<div class="flex items-center justify-between py-3.5 px-4 bg-gray-900 rounded-xl border border-gray-800 hover:border-gray-700 transition ${doneClass}" data-item="${item.name}" data-type="check">
                    <div class="flex items-center gap-4 flex-1 cursor-pointer" onclick="toggleCheck(this, '${item.name}')">
                        <div class="w-6 h-6 rounded-md border-2 flex items-center justify-center transition ${cbClass}">${checkSvg}</div>
                        <span class="text-lg ${labelClass}">${item.name}</span>
                    </div>
                </div>`;
            } else {
                const numVal = parseInt(val) || 0;
                const doneClass = numVal > 0 ? 'opacity-60' : '';
                itemsHtml += `<div class="flex items-center justify-between py-3.5 px-4 bg-gray-900 rounded-xl border border-gray-800 hover:border-gray-700 transition ${doneClass}" data-item="${item.name}" data-type="count">
                    <span class="text-lg text-gray-200 flex-1">${item.name}</span>
                    <input type="number" inputmode="numeric" min="0" class="count-input" data-item="${item.name}" value="${numVal}" onfocus="this.select()" onchange="setCount('${item.name}', this.value)" onblur="setCount('${item.name}', this.value)">
                </div>`;
            }
        }

        const sectionId = 'sect-' + cat.replace(/ /g, '-').replace(/&/g, 'and');
        html += `<section class="mb-6">
            <button onclick="toggleSection('${sectionId}')" class="w-full flex items-center justify-between py-3 group">
                <h2 class="text-base font-semibold text-gray-300 uppercase tracking-wider">${cat}</h2>
                <div class="flex items-center gap-2">
                    <span class="text-sm text-gray-400">${catDone}/${items.length}</span>
                    <svg class="w-4 h-4 text-gray-500 group-hover:text-gray-300 transition sect-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                </div>
            </button>
            <div id="${sectionId}" class="space-y-2">${itemsHtml}</div>
        </section>`;
    }

    container.innerHTML = html;

    // Update progress bar
    const pct = totalItems ? Math.round(totalDone / totalItems * 100) : 0;
    const text = document.getElementById('progress-text');
    const bar = document.getElementById('progress-bar');
    if (text) text.textContent = `${totalDone}/${totalItems} (${pct}%)`;
    if (bar) bar.style.width = `${pct}%`;
}

// Handle browser back/forward
window.addEventListener('popstate', async (e) => {
    if (e.state && e.state.date) {
        currentDate = e.state.date;
        updateDateDisplays();
        try {
            const [configRes, logRes] = await Promise.all([
                fetch(`/api/checklist/config?date=${currentDate}`),
                fetch(`/api/checklist/${currentDate}`),
            ]);
            const configData = await configRes.json();
            const logData = await logRes.json();
            if (configData.ok && logData.ok) {
                rebuildHabitSections(configData.config, logData.completions);
            }
        } catch (err) {}
        if (typeof loadSpend === 'function') loadSpend();
    }
});

// Format date display
document.addEventListener('DOMContentLoaded', () => {
    const display = document.getElementById('date-display');
    const label = document.getElementById('date-label');
    if (display) {
        const d = new Date(currentDate + 'T12:00:00');
        const now = new Date(); const today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
        display.textContent = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        if (currentDate === today) {
            label.textContent = 'Today';
            label.className = 'text-xs text-green-400';
        } else {
            label.textContent = currentDate;
        }
    }

    // Also update spend date display
    const spendDate = document.getElementById('spend-date-display');
    if (spendDate) {
        const d = new Date(currentDate + 'T12:00:00');
        spendDate.textContent = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }

    // Personal tab date
    const personalDate = document.getElementById('personal-date');
    if (personalDate) {
        const d = new Date(currentDate + 'T12:00:00');
        personalDate.textContent = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }

    // Default tab is 'today' — fire its queue loader
    runSubpillLoader(activeTab, activeSubpill[activeTab]);

    // Also warm Personal habits (light call) since it's behind the default tab
    if (typeof loadCommandCenter === 'function') loadCommandCenter();
    if (typeof loadSpend === 'function') loadSpend();
});

// --- Section Toggle ---
function toggleSection(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('hidden');
}

// --- Checklist Toggle ---
async function toggleCheck(el, itemName) {
    const row = el.closest('[data-item]');
    const checkbox = el.querySelector('div');
    const label = el.querySelector('span');
    const isDone = checkbox.classList.contains('bg-green-600');
    const newValue = isDone ? 'FALSE' : 'TRUE';

    // Optimistic UI
    if (newValue === 'TRUE') {
        checkbox.classList.add('bg-green-600', 'border-green-600');
        checkbox.classList.remove('border-gray-600');
        checkbox.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
        label.classList.add('line-through', 'text-gray-500');
        label.classList.remove('text-gray-200');
        row.classList.add('opacity-60');
    } else {
        checkbox.classList.remove('bg-green-600', 'border-green-600');
        checkbox.classList.add('border-gray-600');
        checkbox.innerHTML = '';
        label.classList.remove('line-through', 'text-gray-500');
        label.classList.add('text-gray-200');
        row.classList.remove('opacity-60');
    }

    updateProgress();

    try {
        const res = await fetch('/api/checklist/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: currentDate, item: itemName, value: newValue }),
        });
        const data = await res.json();
        if (!data.ok) showToast(`Failed: ${data.error}`, 'error');
    } catch (err) {
        showToast('Network error', 'error');
    }
}

// --- Count Input (direct number) ---
async function setCount(itemName, rawValue) {
    const value = Math.max(0, parseInt(rawValue) || 0);
    const input = document.querySelector(`.count-input[data-item="${itemName}"]`);
    if (input) input.value = value;

    const row = input ? input.closest('[data-item]') : null;
    if (row) {
        if (value > 0) row.classList.add('opacity-60');
        else row.classList.remove('opacity-60');
    }

    updateProgress();

    try {
        const res = await fetch('/api/checklist/count', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: currentDate, item: itemName, value: String(value) }),
        });
        const data = await res.json();
        if (!data.ok) showToast(`Failed: ${data.error}`, 'error');
    } catch (err) {
        showToast('Network error', 'error');
    }
}

// --- Progress Update ---
function updateProgress() {
    const items = document.querySelectorAll('[data-item][data-type]');
    let total = 0, done = 0;
    items.forEach(item => {
        total++;
        if (item.dataset.type === 'check') {
            const cb = item.querySelector('.bg-green-600');
            if (cb) done++;
        } else {
            const input = item.querySelector('.count-input');
            if (input && parseInt(input.value) > 0) done++;
        }
    });

    const pct = total ? Math.round(done / total * 100) : 0;
    const text = document.getElementById('progress-text');
    const bar = document.getElementById('progress-bar');
    if (text) text.textContent = `${done}/${total} (${pct}%)`;
    if (bar) bar.style.width = `${pct}%`;
}

// --- Toast ---
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-20 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg text-sm font-medium z-[60] transition-all
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
