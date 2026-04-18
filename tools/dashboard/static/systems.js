// Systems pill — automations + services

function _relTimeSys(iso) {
    if (!iso) return 'never';
    try {
        const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
        return `${Math.floor(diff/86400)}d ago`;
    } catch { return iso; }
}

function _dotColor(status) {
    const s = (status || '').toLowerCase();
    if (s === 'green' || s === 'ok' || s === 'healthy') return 'bg-emerald-500';
    if (s === 'amber' || s === 'warn' || s === 'warning') return 'bg-amber-500';
    if (s === 'red' || s === 'error' || s === 'fail') return 'bg-red-500';
    return 'bg-gray-500';
}

function _statusBadge(status) {
    const s = (status || '').toLowerCase();
    const cls = s === 'green' || s === 'ok' ? 'bg-emerald-900/40 text-emerald-300'
              : s === 'amber' || s === 'warn' ? 'bg-amber-900/40 text-amber-300'
              : s === 'red' || s === 'fail' ? 'bg-red-900/40 text-red-300'
              : 'bg-gray-800 text-gray-400';
    return `<span class="px-2 py-0.5 rounded text-[10px] uppercase tracking-wider ${cls}">${status || 'unknown'}</span>`;
}

async function loadSystems() {
    const svcEl = document.getElementById('systems-services');
    const autoEl = document.getElementById('systems-automations');
    if (svcEl) svcEl.innerHTML = '<div class="text-gray-400 italic text-center py-4 text-sm col-span-2">Loading...</div>';
    if (autoEl) autoEl.innerHTML = '<div class="text-gray-400 italic text-center py-4 text-sm">Loading...</div>';

    try {
        const [svcRes, autoRes] = await Promise.all([
            fetch('/api/brand/systems/services'),
            fetch('/api/brand/systems/automations'),
        ]);
        const svcData = await svcRes.json();
        const autoData = await autoRes.json();

        if (svcEl) {
            const services = (svcData.ok && svcData.services) || [];
            svcEl.innerHTML = services.length
                ? services.map(s => `<div class="bg-gray-900 border border-gray-800 rounded-xl p-3 flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full ${_dotColor(s.status)}"></span>
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-medium text-gray-100 truncate">${_esc(s.name||'')}</div>
                        <div class="text-[11px] text-gray-500 truncate">${_esc(s.detail||'')}</div>
                    </div>
                </div>`).join('')
                : '<div class="text-gray-500 text-sm col-span-2 text-center py-3">No services</div>';
        }

        if (autoEl) {
            const list = (autoData.ok && autoData.automations) || [];
            autoEl.innerHTML = list.length
                ? list.map(a => `<div class="bg-gray-900 border border-gray-800 rounded-xl p-3">
                    <div class="flex items-start justify-between gap-2 mb-2">
                        <div class="min-w-0 flex-1">
                            <div class="text-sm font-medium text-gray-100">${_esc(a.friendly_name||a.label||'')}</div>
                            <div class="text-[11px] text-gray-500">${_esc(a.schedule||'')}</div>
                        </div>
                        ${_statusBadge(a.status)}
                    </div>
                    <div class="text-[11px] text-gray-500 mb-2">Last run: ${_relTimeSys(a.last_run)}${a.last_exit_code !== undefined && a.last_exit_code !== null ? ` · exit ${a.last_exit_code}` : ''}</div>
                    <div class="flex gap-2">
                        <button onclick="openAutomationLog('${_esc(a.label||'')}', '${_esc(a.friendly_name||a.label||'')}')"
                                class="flex-1 min-h-[44px] py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs">Log</button>
                        <button onclick="runAutomation('${_esc(a.label||'')}', this)"
                                class="flex-1 min-h-[44px] py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs">Run now</button>
                    </div>
                </div>`).join('')
                : '<div class="text-gray-500 text-sm text-center py-3">No automations</div>';
        }
    } catch (err) {
        if (autoEl) autoEl.innerHTML = `<div class="text-red-400 text-sm">${err.message}</div>`;
    }
}

function _esc(s) {
    return (s || '').toString().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;');
}

async function openAutomationLog(label, title) {
    const modal = document.getElementById('log-modal');
    const body = document.getElementById('log-modal-body');
    const titleEl = document.getElementById('log-modal-title');
    if (!modal || !body) return;
    if (titleEl) titleEl.textContent = title || label;
    body.textContent = 'Loading...';
    modal.classList.remove('hidden');
    try {
        const res = await fetch(`/api/brand/systems/automations/${encodeURIComponent(label)}/log`);
        const data = await res.json();
        body.textContent = data.ok ? (data.log || '(empty)') : (data.error || 'Failed to load log');
    } catch (err) {
        body.textContent = err.message;
    }
}

function closeLogModal() {
    const modal = document.getElementById('log-modal');
    if (modal) modal.classList.add('hidden');
}

async function runAutomation(label, btn) {
    if (btn) { btn.disabled = true; btn.textContent = 'Running...'; }
    try {
        const res = await fetch(`/api/brand/systems/automations/${encodeURIComponent(label)}/run`, { method: 'POST' });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Run failed');
        showToast(data.message || `Started (pid ${data.pid})`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Run now'; }
        setTimeout(loadSystems, 1500);
    }
}

window.loadSystems = loadSystems;
window.openAutomationLog = openAutomationLog;
window.closeLogModal = closeLogModal;
window.runAutomation = runAutomation;
