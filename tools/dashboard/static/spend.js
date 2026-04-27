// Spend Tracker — inline quick-add + daily log + monthly stacked chart
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
    loadSpendMonthlyBars();
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

// --- Monthly stacked bar chart ---

async function loadSpendMonthlyBars() {
    const barsEl = document.getElementById('spend-month-bars');
    const axisEl = document.getElementById('spend-month-axis');
    const labelEl = document.getElementById('spend-month-label');
    const totalEl = document.getElementById('spend-month-total');
    const avgEl = document.getElementById('spend-month-avg');
    const takeoutEl = document.getElementById('spend-month-takeout');
    const generalEl = document.getElementById('spend-month-general');
    const daysEl = document.getElementById('spend-month-days');
    if (!barsEl) return;

    try {
        const res = await fetch('/api/spend/monthly');
        const data = await res.json();
        if (!data.ok) return;

        const days = data.days || [];
        const max = Math.max(...days.map(d => d.total), 1);

        if (labelEl) labelEl.textContent = data.month;
        if (totalEl) totalEl.textContent = `₱${Math.round(data.month_total).toLocaleString()}`;
        if (avgEl) avgEl.textContent = `₱${Math.round(data.daily_avg).toLocaleString()}`;
        if (takeoutEl) takeoutEl.textContent = `₱${Math.round(data.month_takeout).toLocaleString()}`;
        if (generalEl) generalEl.textContent = `₱${Math.round(data.month_general).toLocaleString()}`;
        if (daysEl) daysEl.textContent = data.days_with_spend;

        barsEl.innerHTML = days.map(d => {
            const totalPct = (d.total / max) * 100;
            const takeoutPct = d.total > 0 ? (d.takeout / d.total) * totalPct : 0;
            const generalPct = d.total > 0 ? (d.general / d.total) * totalPct : 0;
            const minVisible = d.total > 0 ? 6 : 2;
            const totalH = Math.max(totalPct, minVisible);

            const empty = d.total === 0;
            const ring = d.is_today ? 'ring-2 ring-blue-400/70 ring-offset-1 ring-offset-gray-900' : '';
            const opacity = d.is_today ? '' : 'opacity-90 hover:opacity-100';

            const title = empty
                ? `Day ${d.day_num} — no spend`
                : `Day ${d.day_num}: ₱${Math.round(d.total).toLocaleString()}` +
                  (d.takeout > 0 ? `\n  Takeout ₱${Math.round(d.takeout).toLocaleString()}` : '') +
                  (d.general > 0 ? `\n  General ₱${Math.round(d.general).toLocaleString()}` : '');

            if (empty) {
                return `<div class="flex-1 flex flex-col justify-end" style="min-width:6px" title="${title}">
                    <div class="bg-gray-800/60 rounded-sm w-full" style="height:${minVisible}%"></div>
                </div>`;
            }

            return `<div class="flex-1 flex flex-col justify-end transition-all ${opacity}" style="min-width:6px" title="${title}">
                <div class="rounded-sm overflow-hidden flex flex-col justify-end ${ring}" style="height:${totalH}%">
                    <div class="bg-blue-500 w-full" style="height:${totalH > 0 ? (generalPct / totalH) * 100 : 0}%"></div>
                    <div class="bg-amber-500 w-full" style="height:${totalH > 0 ? (takeoutPct / totalH) * 100 : 0}%"></div>
                </div>
            </div>`;
        }).join('');

        if (axisEl) {
            const ticks = [1, 8, 15, 22, days.length].filter((v, i, a) => a.indexOf(v) === i);
            axisEl.innerHTML = days.map(d => {
                const show = ticks.includes(d.day_num);
                const isToday = d.is_today;
                return `<span class="flex-1 text-center ${isToday ? 'text-blue-400 font-semibold' : ''}" style="min-width:6px">${show ? d.day_num : ''}</span>`;
            }).join('');
        }
    } catch (err) {
        console.error('Monthly bars failed:', err);
    }
}

// --- Habits stats ---

async function loadHabitsStats() {
    const el = document.getElementById('habits-stats-list');
    if (!el) return;
    el.innerHTML = '<div class="text-gray-400 italic text-center py-8 text-sm">Loading...</div>';
    try {
        const res = await fetch('/api/habits/stats');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Failed');

        const items = data.items || [];
        if (!items.length) {
            el.innerHTML = '<div class="text-gray-500 text-sm text-center py-6">No habit data yet.</div>';
            return;
        }

        el.innerHTML = items.map(item => {
            const streakColor = item.streak >= 7 ? 'text-green-400' :
                                item.streak >= 3 ? 'text-blue-400' :
                                item.streak >= 1 ? 'text-yellow-400' : 'text-gray-600';
            const pctColor = item.pct >= 70 ? 'bg-green-500' :
                             item.pct >= 40 ? 'bg-blue-500' : 'bg-gray-600';
            const dots = (item.history || []).map(done =>
                `<span class="inline-block w-2 h-2 rounded-sm ${done ? pctColor : 'bg-gray-800'}"></span>`
            ).join('');
            return `<div class="bg-gray-900 border border-gray-800 rounded-xl p-3">
                <div class="flex items-center justify-between mb-2">
                    <div>
                        <span class="text-sm font-medium text-gray-100">${item.name}</span>
                        <span class="text-[10px] text-gray-600 ml-2 uppercase tracking-wider">${item.category}</span>
                    </div>
                    <div class="text-right shrink-0 ml-3">
                        <span class="text-lg font-bold ${streakColor}">${item.streak}d</span>
                        <span class="text-[10px] text-gray-500 ml-1">${item.pct}%</span>
                    </div>
                </div>
                <div class="flex gap-0.5 flex-wrap">${dots}</div>
            </div>`;
        }).join('');
    } catch (err) {
        el.innerHTML = `<div class="text-red-400 text-sm text-center py-6">${err.message}</div>`;
    }
}

window.loadHabitsStats = loadHabitsStats;

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
