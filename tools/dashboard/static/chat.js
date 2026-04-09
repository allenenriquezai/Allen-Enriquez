// Claude Chat — Full tab with markdown rendering
// Dependencies: marked.js (loaded from CDN in base.html)

const chatHistory = JSON.parse(localStorage.getItem('enriquez_os_chat') || '[]');

document.addEventListener('DOMContentLoaded', () => {
    renderHistory();
});

function renderHistory() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    container.innerHTML = '';

    if (chatHistory.length === 0) {
        container.innerHTML = '<div class="text-gray-600 text-center py-12 text-sm">Ask Claude anything</div>';
        return;
    }

    chatHistory.forEach(msg => {
        appendMessage(msg.role, msg.content, false);
    });

    container.scrollTop = container.scrollHeight;
}

function appendMessage(role, content, save = true) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    // Remove empty state
    const empty = container.querySelector('.text-center');
    if (empty && save) empty.remove();

    const div = document.createElement('div');

    if (role === 'user') {
        div.className = 'flex justify-end';
        div.innerHTML = `<div class="bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2 max-w-[80%] text-sm">${escapeHtml(content)}</div>`;
    } else if (role === 'assistant') {
        div.className = 'flex justify-start';
        const rendered = typeof marked !== 'undefined' ? marked.parse(content) : escapeHtml(content);
        div.innerHTML = `<div class="bg-gray-800 text-gray-200 rounded-2xl rounded-bl-md px-4 py-2 max-w-[80%] text-sm prose prose-invert prose-sm">${rendered}</div>`;
    } else if (role === 'loading') {
        div.className = 'flex justify-start';
        div.id = 'chat-loading';
        div.innerHTML = `<div class="bg-gray-800 text-gray-400 rounded-2xl rounded-bl-md px-4 py-2 text-sm flex items-center gap-2">
            <span class="animate-pulse">Thinking...</span>
        </div>`;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    if (save && role !== 'loading') {
        chatHistory.push({ role, content });
        localStorage.setItem('enriquez_os_chat', JSON.stringify(chatHistory));
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    appendMessage('user', message);
    appendMessage('loading', '');

    const btn = document.getElementById('chat-send-btn');
    btn.disabled = true;
    btn.textContent = '...';

    try {
        const res = await fetch('/api/claude/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        const data = await res.json();

        const loading = document.getElementById('chat-loading');
        if (loading) loading.remove();

        if (data.ok) {
            appendMessage('assistant', data.response);
        } else {
            appendMessage('assistant', `Error: ${data.error || 'Unknown error'}`);
        }
    } catch (err) {
        const loading = document.getElementById('chat-loading');
        if (loading) loading.remove();
        appendMessage('assistant', 'Network error — could not reach Claude.');
    }

    btn.disabled = false;
    btn.textContent = 'Send';
}

function clearChat() {
    chatHistory.length = 0;
    localStorage.removeItem('enriquez_os_chat');
    renderHistory();
    // Clear server-side conversation memory too
    fetch('/api/claude/clear', { method: 'POST', headers: { 'Content-Type': 'application/json' } }).catch(() => {});
}

// --- Floating chat panel toggle ---
function toggleChatPanel() {
    const panel = document.getElementById('chat-panel');
    const backdrop = document.getElementById('chat-backdrop');
    const fab = document.getElementById('chat-fab');
    if (!panel) return;

    const isOpen = panel.classList.contains('open');
    if (isOpen) {
        panel.classList.remove('open');
        backdrop.classList.remove('open');
        if (fab) fab.style.display = '';
    } else {
        panel.classList.add('open');
        backdrop.classList.add('open');
        if (fab) fab.style.display = 'none';
        const input = document.getElementById('chat-input');
        if (input) setTimeout(() => input.focus(), 300);
    }
}

// Close chat panel on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const panel = document.getElementById('chat-panel');
        if (panel && panel.classList.contains('open')) {
            toggleChatPanel();
        }
    }
});
