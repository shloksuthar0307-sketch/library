/**
 * Premium Library Platform - Core JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSpotlight();
    initSidebar();
});

/* Theme Management */
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    const themeToggles = document.querySelectorAll('.theme-toggle');
    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        });
    });
}

/* Spotlight Effect for Cards */
function initSpotlight() {
    const cards = document.querySelectorAll('.glass-panel');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

/* Sidebar Toggle */
function initSidebar() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const body = document.body;
            if (body.getAttribute('data-sidebar') === 'collapsed') {
                body.removeAttribute('data-sidebar');
            } else {
                body.setAttribute('data-sidebar', 'collapsed');
            }
        });
    }
}

/* Toast Notification System */
window.Toast = {
    show: function(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `glass-panel toast toast-${type} px-4 py-3 mb-2 flex items-center gap-3`;
        toast.style.animation = 'toastSlideIn 0.3s forwards';
        
        let icon = '';
        if (type === 'success') icon = '<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
        else if (type === 'error') icon = '<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>';
        
        toast.innerHTML = `
            ${icon}
            <span class="text-sm font-medium text-[var(--color-text)]">${message}</span>
        `;
        
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toastSlideOut 0.3s forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

/* Handle Django CSRF */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
