// Spend Tracker — inline quick-add + daily log + weekly/monthly views
// Depends on: showToast() from app.js, currentDate global

let spendData = { entries: [], totals: { takeout: 0, general: 0, total: 0 } };

async function loadSpend() {
    try {
        const res = await fetch(`/api/spend/${currentDate}`);
        const data = await res.json();
        if (data.ok) {
            spendData = data;
            renderSpend();
        }
    } catch (err) {
        console.error('Failed to load spend:', err);
    }
    loadSpendWeekly();
    loadSpendMonthly();
}

function renderSpend() {
    const totalsEl = document.getElementById('spend-totals');
    const listEl = document.getElementById('spend-list');
    if (!totalsEl || !listEl) return;

    const t = spendData.totals;
    totalsEl.innerHTML = `
        <span class="text-amber-400">Takeout: ₱${Math.round(t.takeout).toLocaleString()}</span>
        <span class="text-gray-600 mx-2">|</span>
        <span class="text-blue-400">General: ₱${Math.round(t.general).toLocaleString()}</span>
        <span class="text-gray-600 mx-2">|</span>
        <span class="text-white font-medium">Total: ₱${Math.round(t.total).toLocaleString()}</span>
    `;

    if (spendData.entries.length === 0) {
        listEl.innerHTML = '<div class="text-center text-gray-600 text-sm py-4">No spend logged today</div>';
        return;
    }

    listEl.innerHTML = spendData.entries.map((e, i) => `
        <div class="flex items-center justify-between py-2 px-3 bg-gray-800/50 rounded-lg group">
            <div class="flex items-center gap-3">
                <span class="text-xs px-2 py-0.5 rounded ${
                    e.category.toLowerCase() === 'takeout'
                        ? 'bg-amber-900/50 text-amber-400'
                        : 'bg-blue-900/50 text-blue-400'
                }">${e.category}</span>
                <span class="text-sm text-gray-300">₱${Math.round(parseFloat(e.amount)).toLocaleString()}</span>
                ${e.description ? `<span class="text-xs text-gray-500">${e.description}</span>` : ''}
            </div>
            <button onclick="deleteSpend(${i})" class="text-gray-600 hover:text-red-400 transition opacity-0 group-hover:opacity-100">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    `).join('');
}

// --- Inline quick-add ---

async function quickAddSpend(category) {
    const input = document.getElementById('spend-quick-amount');
    if (!input) return;
    const amount = input.value.trim();
    if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
        showToast('Enter an amount first', 'error');
        input.focus();
        return;
    }

    const btn = document.getElementById(`spend-quick-${category.toLowerCase()}`);
    if (btn) { btn.disabled = true; btn.textContent = '...'; }

    try {
        const res = await fetch('/api/spend/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: currentDate,
                category,
                amount: parseFloat(amount).toFixed(2),
                description: '',
            }),
        });
        const data = await res.json();
        if (data.ok) {
            showToast(`₱${Math.round(parseFloat(amount)).toLocaleString()} ${category} logged`, 'success');
            input.value = '';
            loadSpend();
        } else {
            showToast(`Failed: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }

    if (btn) { btn.disabled = false; btn.textContent = category; }
}

// --- Weekly bars ---

async function loadSpendWeekly() {
    const el = document.getElementById('spend-week-bars');
    if (!el) return;
    try {
        const res = await fetch('/api/spend/weekly');
        const data = await res.json();
        if (!data.ok) return;

        const days = data.days || [];
        const max = Math.max(...days.map(d => d.total), 1);

        const totalEl = document.getElementById('spend-week-total');
        if (totalEl) totalEl.textContent = `₱${Math.round(data.week_total).toLocaleString()}`;

        el.innerHTML = days.map(d => {
            const pct = Math.round((d.total / max) * 100);
            const isToday = d.is_today;
            const barColor = isToday ? 'bg-blue-500' : 'bg-gray-600';
            const labelColor = isToday ? 'text-blue-400 font-semibold' : 'text-gray-500';
            const amtColor = isToday ? 'text-white' : 'text-gray-400';
            return `
                <div class="flex-1 flex flex-col items-center gap-1">
                    <div class="text-[10px] ${amtColor}">${d.total > 0 ? Math.round(d.total / 1000) + 'k' : ''}</div>
                    <div class="w-full flex flex-col justify-end" style="height:40px">
                        <div class="${barColor} rounded-t w-full transition-all" style="height:${Math.max(pct, d.total > 0 ? 8 : 2)}%"></div>
                    </div>
                    <div class="text-[10px] ${labelColor}">${d.day}</div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Weekly spend failed:', err);
    }
}

// --- Monthly summary ---

async function loadSpendMonthly() {
    const el = document.getElementById('spend-month-summary');
    if (!el) return;
    try {
        const res = await fetch('/api/spend/monthly');
        const data = await res.json();
        if (!data.ok) return;

        el.innerHTML = `
            <span class="text-gray-400 text-xs">${data.month}</span>
            <span class="text-white font-medium">₱${Math.round(data.month_total).toLocaleString()}</span>
            <span class="text-gray-600 mx-1">·</span>
            <span class="text-gray-400 text-xs">avg ₱${Math.round(data.daily_avg).toLocaleString()}/day</span>
        `;
    } catch (err) {
        console.error('Monthly spend failed:', err);
    }
}

// --- Delete ---

async function deleteSpend(index) {
    try {
        const res = await fetch(`/api/spend/${currentDate}/${index}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            showToast('Removed', 'success');
            loadSpend();
        } else {
            showToast(`Failed: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}
