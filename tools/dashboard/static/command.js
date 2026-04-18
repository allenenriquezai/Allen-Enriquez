// Home — Weekly Overview

async function loadCommandCenter() {
    try {
        const [weeklyRes, spendRes, cmdRes, outreachRes] = await Promise.all([
            fetch(`/api/checklist/weekly?end=${currentDate}`),
            fetch('/api/spend/summary?period=week'),
            fetch('/api/command-center'),
            fetch('/api/outreach/detailed'),
        ]);
        const weekly = await weeklyRes.json();
        const spend = await spendRes.json();
        const cmd = await cmdRes.json();
        const outreach = await outreachRes.json();

        renderWeekOverview(weekly, spend, cmd);
        if (outreach.ok) renderOutreachDashboard(outreach);
        loadCoachCard();
    } catch (err) {
        console.error('Home load failed:', err);
    }
}

async function loadCoachCard() {
    const el = document.getElementById('coach-text');
    if (!el) return;
    try {
        const res = await fetch('/api/coach/daily');
        const data = await res.json();
        if (data.ok && data.text) {
            el.textContent = data.text;
        } else {
            el.innerHTML = '<span class="text-gray-500 italic">Coach offline.</span>';
        }
    } catch (err) {
        el.innerHTML = '<span class="text-gray-500 italic">Coach offline.</span>';
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

}

function renderOutreachDashboard(data) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    const t = data.today;

    // Goal ring
    set('goal-num', t.total);
    set('goal-target', data.goal);
    const ring = document.getElementById('goal-ring');
    if (ring) {
        const circumference = 213.6;
        const pct = Math.min(t.total / data.goal, 1);
        ring.style.strokeDashoffset = circumference * (1 - pct);
        ring.style.stroke = pct >= 1 ? '#10b981' : pct >= 0.5 ? '#3b82f6' : '#ef4444';
    }

    // Today stats
    set('ot-convos', t.convos);
    set('ot-no-answer', t.no_answer);
    set('ot-warm', t.warm);

    // Outcome bars
    const barsEl = document.getElementById('outcome-bars');
    if (barsEl && t.total > 0) {
        const outcomes = [
            { label: 'No Answer', count: t.no_answer, color: 'bg-gray-500' },
            { label: 'Hung Up', count: t.hung_up, color: 'bg-red-500' },
            { label: 'Not Interested', count: t.not_interested, color: 'bg-red-400' },
            { label: 'Invalid', count: t.invalid, color: 'bg-gray-600' },
            { label: 'Callback', count: t.callback, color: 'bg-blue-500' },
            { label: 'Email', count: t.email, color: 'bg-cyan-500' },
            { label: 'Warm Interest', count: t.warm, color: 'bg-amber-500' },
            { label: 'Meeting', count: t.meeting, color: 'bg-emerald-500' },
        ].filter(o => o.count > 0);

        barsEl.innerHTML = outcomes.map(o => {
            const pct = Math.round(o.count / t.total * 100);
            return `<div class="flex items-center gap-2">
                <div class="w-24 text-[11px] text-gray-400 text-right truncate">${o.label}</div>
                <div class="flex-1 bg-gray-800 rounded-full h-2.5 overflow-hidden">
                    <div class="${o.color} h-full rounded-full transition-all duration-500" style="width:${pct}%"></div>
                </div>
                <div class="w-10 text-[11px] text-gray-400 text-right">${o.count}</div>
            </div>`;
        }).join('');
    } else if (barsEl) {
        barsEl.innerHTML = '<div class="text-xs text-gray-600 text-center py-2">No calls yet</div>';
    }

    // Week summary
    set('ow-total', data.week.total);
    set('ow-rate', t.conv_rate + '%');
    set('ow-streak', data.streak + 'd');

    // 14-day trend chart
    const chartEl = document.getElementById('trend-chart');
    if (chartEl && data.trend) {
        const maxCalls = Math.max(...data.trend.map(d => d.calls), 1);
        chartEl.innerHTML = data.trend.map(d => {
            const h = Math.max(d.calls / maxCalls * 100, 2);
            const isToday = d === data.trend[data.trend.length - 1];
            const barColor = d.calls >= data.goal ? 'bg-emerald-500'
                           : d.calls >= data.goal * 0.5 ? 'bg-blue-500'
                           : d.calls > 0 ? 'bg-gray-600'
                           : 'bg-gray-800';
            const border = isToday ? 'ring-1 ring-white/30' : '';
            return `<div class="flex-1 flex flex-col items-center gap-1 group relative">
                <div class="w-full ${barColor} ${border} rounded-sm transition-all duration-300 cursor-default"
                     style="height:${h}%" title="${d.date}: ${d.calls} calls, ${d.convos} convos"></div>
                <div class="text-[9px] text-gray-600 ${isToday ? 'text-white font-bold' : ''}">${d.day.slice(0,2)}</div>
            </div>`;
        }).join('');
    }

    // Coaching nudges
    const nudgesEl = document.getElementById('nudges-container');
    if (nudgesEl && data.nudges && data.nudges.length > 0) {
        const icons = {
            action: '<svg class="w-4 h-4 text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
            push: '<svg class="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
            warning: '<svg class="w-4 h-4 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.072 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>',
            insight: '<svg class="w-4 h-4 text-cyan-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>',
            win: '<svg class="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        };
        const borders = {
            action: 'border-blue-800/50', push: 'border-amber-800/50',
            warning: 'border-red-800/50', insight: 'border-cyan-800/50', win: 'border-emerald-800/50',
        };
        nudgesEl.innerHTML = data.nudges.map(n =>
            `<div class="bg-gray-900 border ${borders[n.type] || 'border-gray-800'} rounded-xl px-4 py-3 flex items-start gap-3">
                ${icons[n.type] || ''}
                <div class="text-xs text-gray-300 leading-relaxed">${n.text}</div>
            </div>`
        ).join('');
    }
}

// Load on page ready
document.addEventListener('DOMContentLoaded', () => {
    loadCommandCenter();
});
