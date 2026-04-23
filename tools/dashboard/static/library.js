// Enriquez OS — Library (Notes + Projects + Links)
// Hits /api/library/<collection>{,/<id>} for CRUD.

const _libraryCache = { notes: null, projects: null, links: null };

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
        if (collection === 'links') {
            _libraryCache.links = data.links || [];
            renderLibraryLinks(_libraryCache.links);
        } else {
            _libraryCache[collection] = data.items || [];
            renderLibraryList(collection, _libraryCache[collection]);
        }
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

// ============================================================
// Links collection (different API contract: returns data.links)
// ============================================================

function renderLibraryLinks(links) {
    const listEl = document.getElementById('library-links-list');
    if (!listEl) return;

    if (!links || links.length === 0) {
        listEl.innerHTML = '<div class="text-gray-500 text-center py-8 text-sm">No links yet — tap + to add one</div>';
        return;
    }

    // Group by section
    const sections = {};
    const order = [];
    for (const link of links) {
        const sec = link.section || 'Uncategorized';
        if (!sections[sec]) { sections[sec] = []; order.push(sec); }
        sections[sec].push(link);
    }

    listEl.innerHTML = order.map(sec => `
        <div class="mb-4">
            <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-2 px-1">${escapeHtml(sec)}</div>
            <div class="space-y-1.5">
                ${sections[sec].map(link => `
                    <div class="flex items-start justify-between bg-gray-900 border border-gray-800 rounded-xl p-3 hover:border-gray-700 transition">
                        <a href="${escapeHtml(link.url)}" target="_blank" rel="noopener" class="flex-1 min-w-0 mr-3">
                            <div class="text-sm text-blue-400 hover:text-blue-300 truncate">${escapeHtml(link.title || link.url)}</div>
                            ${link.note ? `<div class="text-xs text-gray-500 mt-0.5">${escapeHtml(link.note)}</div>` : ''}
                        </a>
                        <button onclick="deleteLink(${link.index})" class="text-gray-600 hover:text-red-400 transition shrink-0 mt-0.5">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function openLinksModal() {
    const modal = document.getElementById('links-modal');
    if (!modal) return;
    document.getElementById('link-url').value = '';
    document.getElementById('link-title').value = '';
    document.getElementById('link-note').value = '';
    document.getElementById('link-section').value = '';
    modal.classList.remove('hidden');
    setTimeout(() => document.getElementById('link-url').focus(), 100);
}

function closeLinksModal() {
    const modal = document.getElementById('links-modal');
    if (modal) modal.classList.add('hidden');
}

async function saveLink() {
    const url = document.getElementById('link-url').value.trim();
    if (!url) {
        if (typeof showToast === 'function') showToast('URL required', 'error');
        return;
    }
    const title = document.getElementById('link-title').value.trim();
    const note = document.getElementById('link-note').value.trim();
    const section = document.getElementById('link-section').value.trim() || 'Uncategorized';

    const btn = document.getElementById('link-save-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/library/links', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, title, note, section }),
        });
        const data = await res.json();
        if (data.ok) {
            if (typeof showToast === 'function') showToast('Link saved', 'success');
            closeLinksModal();
            _libraryCache.links = null;
            loadLibrary('links');
        } else {
            if (typeof showToast === 'function') showToast(`Failed: ${data.error}`, 'error');
        }
    } catch {
        if (typeof showToast === 'function') showToast('Network error', 'error');
    }

    btn.textContent = 'Save';
    btn.disabled = false;
}

async function deleteLink(index) {
    if (!confirm('Remove this link?')) return;
    try {
        const res = await fetch(`/api/library/links/${index}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            if (typeof showToast === 'function') showToast('Removed', 'success');
            _libraryCache.links = null;
            loadLibrary('links');
        } else {
            if (typeof showToast === 'function') showToast(`Failed: ${data.error}`, 'error');
        }
    } catch {
        if (typeof showToast === 'function') showToast('Network error', 'error');
    }
}
