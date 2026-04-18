// Enriquez OS — Library (Notes + Projects)
// Hits /api/library/<collection>{,/<id>} for CRUD.

const _libraryCache = { notes: null, projects: null };

async function loadLibrary(collection) {
    const listEl = document.getElementById(`library-${collection}-list`);
    if (!listEl) return;

    if (!_libraryCache[collection]) {
        listEl.innerHTML = '<div class="text-gray-400 italic text-center py-8 text-sm">Loading...</div>';
    }

    try {
        const res = await fetch(`/api/library/${collection}`);
        const data = await res.json();
        if (!data.ok) {
            listEl.innerHTML = `<div class="text-red-400 text-center py-8 text-sm">Error: ${data.error || 'failed'}</div>`;
            return;
        }
        _libraryCache[collection] = data.items || [];
        renderLibraryList(collection, _libraryCache[collection]);
    } catch (err) {
        listEl.innerHTML = '<div class="text-red-400 text-center py-8 text-sm">Failed to load</div>';
    }
}

function renderLibraryList(collection, items) {
    const listEl = document.getElementById(`library-${collection}-list`);
    if (!listEl) return;

    if (!items || items.length === 0) {
        listEl.innerHTML = `<div class="text-gray-500 text-center py-8 text-sm">No ${collection} yet — tap + to add one</div>`;
        return;
    }

    listEl.innerHTML = items.map(item => {
        const tags = (item.tags || []).map(t =>
            `<span class="text-[10px] px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">${t}</span>`
        ).join(' ');
        const updated = item.updated ? item.updated.slice(0, 10) : '';
        return `
            <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 cursor-pointer hover:border-gray-700 transition"
                 onclick="openLibraryItem('${collection}', '${item.id}')">
                <div class="flex items-start justify-between mb-1">
                    <div class="text-base font-medium text-gray-200">${escapeHtml(item.title || item.id)}</div>
                    <div class="text-[10px] text-gray-500 ml-2 shrink-0">${updated}</div>
                </div>
                ${item.snippet ? `<div class="text-sm text-gray-500 mb-2">${escapeHtml(item.snippet)}</div>` : ''}
                ${tags ? `<div class="flex gap-1 flex-wrap">${tags}</div>` : ''}
            </div>
        `;
    }).join('');
}

// --- Modal: create + edit ---
function openLibraryModal(collection) {
    document.getElementById('library-collection').value = collection;
    document.getElementById('library-item-id').value = '';
    document.getElementById('library-title').value = '';
    document.getElementById('library-tags').value = '';
    document.getElementById('library-body').value = '';
    document.getElementById('library-modal-title').textContent =
        collection === 'projects' ? 'New Project' : 'New Note';
    document.getElementById('library-delete-btn').classList.add('hidden');
    document.getElementById('library-modal').classList.remove('hidden');
    setTimeout(() => document.getElementById('library-title').focus(), 100);
}

async function openLibraryItem(collection, itemId) {
    try {
        const res = await fetch(`/api/library/${collection}/${itemId}`);
        const data = await res.json();
        if (!data.ok) {
            if (typeof showToast === 'function') showToast('Failed to open', 'error');
            return;
        }
        const item = data.item;
        document.getElementById('library-collection').value = collection;
        document.getElementById('library-item-id').value = item.id;
        document.getElementById('library-title').value = item.title || '';
        document.getElementById('library-tags').value = (item.tags || []).join(', ');
        document.getElementById('library-body').value = item.body || '';
        document.getElementById('library-modal-title').textContent =
            (collection === 'projects' ? 'Edit Project' : 'Edit Note');
        document.getElementById('library-delete-btn').classList.remove('hidden');
        document.getElementById('library-modal').classList.remove('hidden');
    } catch {
        if (typeof showToast === 'function') showToast('Network error', 'error');
    }
}

function closeLibraryModal() {
    document.getElementById('library-modal').classList.add('hidden');
}

async function saveLibraryItem() {
    const collection = document.getElementById('library-collection').value;
    const itemId = document.getElementById('library-item-id').value;
    const title = document.getElementById('library-title').value.trim();
    const tagsRaw = document.getElementById('library-tags').value.trim();
    const body = document.getElementById('library-body').value;

    if (!title) {
        if (typeof showToast === 'function') showToast('Title required', 'error');
        return;
    }

    const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];

    const btn = document.getElementById('library-save-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        const url = itemId
            ? `/api/library/${collection}/${itemId}`
            : `/api/library/${collection}`;
        const method = itemId ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, tags, body }),
        });
        const data = await res.json();
        if (data.ok) {
            if (typeof showToast === 'function') showToast('Saved', 'success');
            closeLibraryModal();
            _libraryCache[collection] = null;
            loadLibrary(collection);
        } else {
            if (typeof showToast === 'function') showToast(`Failed: ${data.error}`, 'error');
        }
    } catch {
        if (typeof showToast === 'function') showToast('Network error', 'error');
    }

    btn.textContent = 'Save';
    btn.disabled = false;
}

async function deleteLibraryItem() {
    const collection = document.getElementById('library-collection').value;
    const itemId = document.getElementById('library-item-id').value;
    if (!itemId) return;
    if (!confirm('Delete this item? This cannot be undone.')) return;

    try {
        const res = await fetch(`/api/library/${collection}/${itemId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            if (typeof showToast === 'function') showToast('Deleted', 'success');
            closeLibraryModal();
            _libraryCache[collection] = null;
            loadLibrary(collection);
        } else {
            if (typeof showToast === 'function') showToast(`Failed: ${data.error}`, 'error');
        }
    } catch {
        if (typeof showToast === 'function') showToast('Network error', 'error');
    }
}

function escapeHtml(s) {
    return (s || '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}
