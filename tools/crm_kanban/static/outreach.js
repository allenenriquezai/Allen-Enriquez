// Outreach kanban — card interactions + drag-drop
(function () {
    const STAGES = ['enriched', 'queued', 'sent', 'replied', 'discovery_booked', 'no_reply', 'not_now', 'optout', 'ad-lead'];

    function flash(el, color) {
        const orig = el.style.background;
        el.style.background = color;
        setTimeout(() => { el.style.background = orig; }, 600);
    }

    async function postJSON(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        return res.json();
    }

    function bindCard(card) {
        const id = parseInt(card.dataset.id, 10);
        if (!id) return;

        // Copy DM button
        const copyBtn = card.querySelector('[data-action="copy"]');
        const ta = card.querySelector('[data-hook-textarea]');
        if (copyBtn && ta) {
            copyBtn.addEventListener('click', async () => {
                const text = ta.value;
                try {
                    await navigator.clipboard.writeText(text);
                    // Persist edits if user changed the textarea before copying
                    if (ta.defaultValue !== text) {
                        await postJSON('/api/outreach/edit-hook', { id, personal_hook: text });
                    }
                    flash(copyBtn, '#10b981');
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => { copyBtn.textContent = 'Copy DM'; }, 1500);
                } catch (e) {
                    console.error('clipboard fail', e);
                    copyBtn.textContent = 'Copy fail';
                }
            });
        }

        // Mark-sent button
        const sentBtn = card.querySelector('[data-action="mark-sent"]');
        if (sentBtn) {
            sentBtn.addEventListener('click', async () => {
                sentBtn.disabled = true;
                sentBtn.textContent = '...';
                const r = await postJSON('/api/outreach/mark-sent', { ids: [id] });
                if (r.ok) {
                    // Move card to Sent column without full reload
                    const sentCol = document.getElementById('col-sent');
                    if (sentCol) sentCol.prepend(card);
                    flash(card, '#065f46');
                    sentBtn.remove();
                } else {
                    sentBtn.textContent = 'Error';
                    sentBtn.disabled = false;
                }
            });
        }

        // Mark-replied buttons
        card.querySelectorAll('[data-action="mark-replied"]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const classification = btn.dataset.classification;
                const r = await postJSON('/api/outreach/mark-replied', { id, classification });
                if (r.ok) {
                    const repliedCol = document.getElementById('col-replied');
                    if (repliedCol) repliedCol.prepend(card);
                    flash(card, '#581c87');
                }
            });
        });
    }

    function bindDragDrop() {
        STAGES.forEach(stage => {
            const col = document.getElementById('col-' + stage);
            if (!col) return;
            new Sortable(col, {
                group: 'outreach',
                animation: 150,
                ghostClass: 'opacity-30',
                onEnd: async evt => {
                    const card = evt.item;
                    const targetStage = evt.to.dataset.stage;
                    const id = parseInt(card.dataset.id, 10);
                    if (!id || !targetStage) return;
                    await postJSON('/api/outreach/move', { id, target_status: targetStage });
                },
            });
        });
    }

    function bindRunButtons() {
        document.querySelectorAll('.run-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const source = btn.dataset.run;
                btn.disabled = true;
                const orig = btn.textContent;
                btn.textContent = '…';
                btn.classList.add('opacity-50');
                try {
                    const res = await postJSON('/api/outreach/run', { source });
                    if (res && res.ok === false && res.error === 'already running') {
                        btn.textContent = 'running';
                    } else {
                        btn.textContent = 'started';
                    }
                    pollRunStatus(source, btn, orig);
                } catch (e) {
                    btn.textContent = 'err';
                    setTimeout(() => { btn.textContent = orig; btn.disabled = false; btn.classList.remove('opacity-50'); }, 3000);
                }
            });
        });
    }

    async function pollRunStatus(source, btn, origLabel) {
        for (let i = 0; i < 120; i++) {  // ~10min cap
            await new Promise(r => setTimeout(r, 5000));
            try {
                const res = await fetch('/api/outreach/run-status').then(r => r.json());
                const s = res.state && res.state[source];
                if (s && !s.running) {
                    const ok = s.returncode === 0;
                    btn.textContent = ok ? '✓ ' + origLabel : '✗ ' + origLabel;
                    btn.title = (s.tail || '').slice(-500);
                    if (ok) setTimeout(() => location.reload(), 1500);
                    setTimeout(() => { btn.textContent = origLabel; btn.disabled = false; btn.classList.remove('opacity-50'); }, 8000);
                    return;
                }
            } catch (e) { /* retry */ }
        }
        btn.textContent = origLabel; btn.disabled = false; btn.classList.remove('opacity-50');
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.card').forEach(bindCard);
        bindDragDrop();
        bindRunButtons();
    });
})();
