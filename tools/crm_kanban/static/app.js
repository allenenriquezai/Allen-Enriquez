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
    // Disable all drag during move
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

// --- Modal ---
function openModal(cardEl) {
    // Don't open if we just finished dragging
    if (cardEl.classList.contains('drag-active')) return;

    currentCard = cardEl;
    const lead = JSON.parse(cardEl.dataset.lead);

    document.getElementById('modal-title').textContent = lead.business_name || '';

    // Populate inputs (hidden by default) and display links
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

        // Reset to display mode
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

    // Editable fields
    document.getElementById('modal-outcome').value = lead.call_outcome || 'New / No Label';
    document.getElementById('modal-followup').value = lead.follow_up_date || '';
    document.getElementById('modal-notes').value = lead.notes || '';

    // Enrichment (read-only)
    document.getElementById('modal-city').textContent = lead.city || '-';
    document.getElementById('modal-source').textContent = lead.source || '-';
    document.getElementById('modal-hook').textContent = lead.personal_hook || '-';
    document.getElementById('modal-called').textContent = lead.date_called || '-';
    document.getElementById('modal-bbb').textContent = lead.bbb_rating || '-';

    // LinkedIn with link
    const liEl = document.getElementById('modal-linkedin');
    if (lead.linkedin) {
        liEl.innerHTML = `<a href="${lead.linkedin}" target="_blank" class="text-blue-400 hover:text-blue-300">${lead.linkedin}</a>`;
    } else {
        liEl.textContent = '-';
    }

    // Social media
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
        'Phone': [document.getElementById('modal-phone').value, lead.phone || ''],
        'Phone 2': [document.getElementById('modal-phone2').value, lead.phone2 || ''],
        'Email': [document.getElementById('modal-email').value, lead.email || ''],
        'Website': [document.getElementById('modal-website').value, lead.website || ''],
        'Call Outcome': [document.getElementById('modal-outcome').value, lead.call_outcome || ''],
        'Follow-up Date': [document.getElementById('modal-followup').value, lead.follow_up_date || ''],
        'Notes': [document.getElementById('modal-notes').value, lead.notes || ''],
    };
    for (const [key, [newVal, oldVal]] of Object.entries(fields)) {
        if (newVal !== oldVal) updates[key] = newVal;
    }

    // Auto-set Date Called to today when outcome changes
    if (updates['Call Outcome']) {
        const now = new Date();
        const day = now.getDate();
        const month = now.toLocaleString('en-GB', { month: 'long' });
        updates['Date Called'] = `${day} ${month}`;
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
            body: JSON.stringify({
                tab: lead.tab,
                row_num: lead.row_num,
                updates: updates,
            }),
        });
        const data = await res.json();

        if (data.ok) {
            showToast('Saved', 'success');
            // Reload to reflect changes (simple approach for v1)
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

// Close modal on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// --- Field display/edit toggle ---
function toggleFieldEdit(field) {
    const input = document.getElementById(`modal-${field}`);
    const display = document.getElementById(`modal-${field}-display`);

    if (input.classList.contains('hidden')) {
        // Switch to edit mode
        display.classList.add('hidden');
        input.classList.remove('hidden');
        input.focus();
    } else {
        // Switch back to display mode — update display from input value
        const val = input.value.trim();
        input.classList.add('hidden');
        display.classList.remove('hidden');

        if (val) {
            display.textContent = val;
            const fieldEl = display.closest('.linkable-field');
            const type = field === 'phone' || field === 'phone2' ? 'tel'
                       : field === 'email' ? 'mailto'
                       : field === 'website' ? 'url' : 'text';
            if (type === 'tel') display.href = `tel:${val}`;
            else if (type === 'mailto') display.href = `mailto:${val}`;
            else if (type === 'url') display.href = val.startsWith('http') ? val : `https://${val}`;
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
