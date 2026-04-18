// Files pill (Vault) — list + upload to Drive

function _escF(s) {
    return (s || '').toString().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function loadFiles() {
    const list = document.getElementById('vault-files-list');
    if (!list) return;
    list.innerHTML = '<div class="text-gray-400 italic text-center py-8 text-sm">Loading...</div>';
    try {
        const res = await fetch('/api/vault/files/list');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Files failed');
        const files = data.files || [];
        if (!files.length) {
            list.innerHTML = '<div class="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center text-sm text-gray-400">No files yet. Tap Upload.</div>';
            return;
        }
        list.innerHTML = files.map(f => {
            const tags = (f.tags || []).map(t => `<span class="px-1.5 py-0.5 bg-gray-800 text-gray-400 text-[10px] rounded">${_escF(t)}</span>`).join(' ');
            return `<div class="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div class="flex items-start justify-between gap-2 mb-1">
                    <div class="text-sm font-medium text-gray-100 truncate flex-1">${_escF(f.filename||'')}</div>
                    ${f.drive_url ? `<a href="${_escF(f.drive_url)}" target="_blank" class="text-xs text-blue-400 hover:text-blue-300 shrink-0">Drive &rarr;</a>` : ''}
                </div>
                ${tags ? `<div class="flex flex-wrap gap-1 mb-1">${tags}</div>` : ''}
                ${f.caption ? `<div class="text-xs text-gray-400">${_escF(f.caption)}</div>` : ''}
                ${f.uploaded ? `<div class="text-[10px] text-gray-500 mt-1">${_escF(f.uploaded)}</div>` : ''}
            </div>`;
        }).join('');
    } catch (err) {
        list.innerHTML = `<div class="text-red-400 text-sm text-center py-6">${err.message}</div>`;
    }
}

function openFileUpload() {
    const modal = document.getElementById('file-modal');
    if (!modal) return;
    document.getElementById('file-input').value = '';
    document.getElementById('file-tags').value = '';
    document.getElementById('file-caption').value = '';
    modal.classList.remove('hidden');
}

function closeFileModal() {
    const modal = document.getElementById('file-modal');
    if (modal) modal.classList.add('hidden');
}

async function submitFileUpload() {
    const fileInput = document.getElementById('file-input');
    const tags = document.getElementById('file-tags').value;
    const caption = document.getElementById('file-caption').value;
    const btn = document.getElementById('file-upload-btn');
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        showToast('Pick a file first', 'error');
        return;
    }
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    fd.append('tags', tags);
    fd.append('caption', caption);

    if (btn) { btn.disabled = true; btn.textContent = 'Uploading...'; }
    try {
        const res = await fetch('/api/vault/files/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Upload failed');
        showToast('Uploaded', 'success');
        closeFileModal();
        loadFiles();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Upload'; }
    }
}

window.loadFiles = loadFiles;
window.openFileUpload = openFileUpload;
window.closeFileModal = closeFileModal;
window.submitFileUpload = submitFileUpload;
