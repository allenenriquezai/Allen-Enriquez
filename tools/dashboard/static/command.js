// Home — Weekly Overview

async function loadCommandCenter() {
    try {
        const [weeklyRes, spendRes, cmdRes] = await Promise.all([
            fetch(`/api/checklist/weekly?end=${currentDate}`),
            fetch('/api/spend/summary?period=week'),
            fetch('/api/command-center'),
        ]);
        const weekly = await weeklyRes.json();
        const spend = await spendRes.json();
        const cmd = await cmdRes.json();

        renderWeekOverview(weekly, spend, cmd);
    } catch (err) {
        console.error('Home load failed:', err);
    }
}

function renderWeekOverview(weekly, spend, cmd) {
    // 7-day bars
    const barsEl = document.getElementById('week-bars');
    if (barsEl && weekly.ok && weekly.days) {
        let html = '';
        weekly.days.forEach(d => {
            const color = d.pct >= 80 ? 'bg-green-600'
                        : d.pct >= 50 ? 'bg-amber-600'
                        : d.pct > 0  ? 'bg-red-600'
                        : 'bg-gray-800';
            html += `<div class="flex-1 text-center">
                <div class="text-xs text-gray-400 mb-1">${d.day}</div>
                <div class="h-10 ${color} rounded-lg flex items-center justify-center text-xs font-semibold text-white">${d.pct}%</div>
            </div>`;
        });
        barsEl.innerHTML = html;
    }

    // Stats
    const avgEl = document.getElementById('stat-avg');
    const spendEl = document.getElementById('stat-spend');
    const streakEl = document.getElementById('stat-streak');

    if (avgEl && weekly.ok) avgEl.textContent = `${weekly.avg_pct}%`;
    if (streakEl && weekly.ok) streakEl.textContent = `${weekly.streak}d`;

    if (spendEl && spend.ok && spend.this_week) {
        spendEl.textContent = `₱${Math.round(spend.this_week.total).toLocaleString()}`;
    }

    // Today's habits card
    if (cmd.ok && cmd.checklist) {
        const c = cmd.checklist;
        const valEl = document.getElementById('cmd-habits-value');
        const barEl = document.getElementById('cmd-habits-bar');
        if (valEl) valEl.textContent = `${c.done}/${c.total} (${c.pct}%)`;
        if (barEl) barEl.style.width = `${c.pct}%`;
    }

    // Today's spend card
    if (cmd.ok && cmd.spend) {
        const spCardEl = document.getElementById('cmd-spend-value');
        if (spCardEl) spCardEl.textContent = `₱${Math.round(cmd.spend.today).toLocaleString()}`;
    }

    // Personal outreach
    if (cmd.ok && cmd.personal_outreach) {
        const p = cmd.personal_outreach;
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('p-today-calls', p.today.calls);
        set('p-today-connected', p.today.connected);
        set('p-today-warm', p.today.warm);
        set('p-week-calls', p.week.calls);
        set('p-week-connected', p.week.connected);
        set('p-week-warm', p.week.warm);
    }

    // EPS outreach
    if (cmd.ok && cmd.eps_outreach) {
        const e = cmd.eps_outreach;
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('e-today-calls', e.today.calls);
        set('e-today-connected', e.today.connected);
        set('e-today-warm', e.today.warm);
        set('e-week-calls', e.week.calls);
        set('e-week-connected', e.week.connected);
        set('e-week-warm', e.week.warm);
    }
}

// Load on page ready
document.addEventListener('DOMContentLoaded', () => {
    loadCommandCenter();
});
