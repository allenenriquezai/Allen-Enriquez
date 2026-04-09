// Enriquez OS Dashboard — Main JS

// Current date (YYYY-MM-DD)
let currentDate = new URLSearchParams(window.location.search).get('date')
    || (() => { const n = new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-${String(n.getDate()).padStart(2,'0')}`; })();

// Active tab
let activeTab = 'home';

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

    // Lazy-load data when switching tabs
    if (tab === 'spend' && typeof loadSpend === 'function') loadSpend();
    if (tab === 'brief') {
        if (typeof loadBrief === 'function') loadBrief(activeBrief);
        if (typeof startBriefRefresh === 'function') startBriefRefresh();
    } else {
        if (typeof stopBriefRefresh === 'function') stopBriefRefresh();
    }
    if (tab === 'learn') {
        if (typeof loadLearning === 'function') loadLearning();
    }
    if (tab === 'home') {
        if (typeof loadCommandCenter === 'function') loadCommandCenter();
    }

    // Scroll to top
    window.scrollTo(0, 0);
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

    // Reload data for the active tab
    try {
        const res = await fetch(`/api/checklist/${currentDate}`);
        const data = await res.json();
        if (data.ok) updateChecklistUI(data.completions);
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
    const homeDate = document.getElementById('home-date');
    if (homeDate) homeDate.textContent = formatted;
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

// Handle browser back/forward
window.addEventListener('popstate', async (e) => {
    if (e.state && e.state.date) {
        currentDate = e.state.date;
        updateDateDisplays();
        try {
            const res = await fetch(`/api/checklist/${currentDate}`);
            const data = await res.json();
            if (data.ok) updateChecklistUI(data.completions);
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

    // Home date
    const homeDate = document.getElementById('home-date');
    if (homeDate) {
        const d = new Date(currentDate + 'T12:00:00');
        homeDate.textContent = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }

    // Load spend data
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
