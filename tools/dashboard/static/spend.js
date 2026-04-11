// Spend Tracker — Quick-add + daily log
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

function openSpendModal(category) {
    const modal = document.getElementById('spend-modal');
    document.getElementById('spend-category').value = category;
    document.getElementById('spend-amount').value = '';
    document.getElementById('spend-desc').value = '';
    modal.classList.remove('hidden');
    // Focus amount input after animation
    setTimeout(() => document.getElementById('spend-amount').focus(), 100);
}

function closeSpendModal() {
    document.getElementById('spend-modal').classList.add('hidden');
}

async function saveSpend() {
    const category = document.getElementById('spend-category').value;
    const amount = document.getElementById('spend-amount').value;
    const description = document.getElementById('spend-desc').value;

    if (!amount || isNaN(parseFloat(amount))) {
        showToast('Enter a valid amount', 'error');
        return;
    }

    const btn = document.getElementById('spend-save-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/spend/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: currentDate,
                category,
                amount: parseFloat(amount).toFixed(2),
                description,
            }),
        });
        const data = await res.json();

        if (data.ok) {
            showToast(`₱${Math.round(parseFloat(amount)).toLocaleString()} ${category} logged`, 'success');
            closeSpendModal();
            loadSpend();
        } else {
            showToast(`Failed: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }

    btn.textContent = 'Save';
    btn.disabled = false;
}

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
