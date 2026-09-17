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
/**
 * Command Palette (Ctrl+K)
 */

document.addEventListener('DOMContentLoaded', () => {
    const palette = document.getElementById('command-palette');
    const input = document.getElementById('command-input');
    const triggers = document.querySelectorAll('.cmd-k-trigger');
    
    if (!palette || !input) return;

    function openPalette() {
        palette.classList.remove('hidden');
        palette.classList.add('flex');
        input.focus();
        input.value = '';
    }

    function closePalette() {
        palette.classList.add('hidden');
        palette.classList.remove('flex');
    }

    // Keyboard shortcut
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (palette.classList.contains('hidden')) {
                openPalette();
            } else {
                closePalette();
            }
        }
        
        if (e.key === 'Escape' && !palette.classList.contains('hidden')) {
            closePalette();
        }
    });

    // Click triggers
    triggers.forEach(t => t.addEventListener('click', (e) => {
        e.preventDefault();
        openPalette();
    }));

    // Backdrop click
    palette.addEventListener('click', (e) => {
        if (e.target === palette) {
            closePalette();
        }
    });

    // Filtering and Keyboard Navigation logic
    const commandList = document.getElementById('command-list');
    if (commandList) {
        const items = Array.from(commandList.querySelectorAll('a'));
        const headers = Array.from(commandList.querySelectorAll('div.uppercase'));
        let selectedIndex = -1;

        function updateSelection() {
            const visibleItems = items.filter(item => item.style.display !== 'none');
            visibleItems.forEach((item, index) => {
                if (index === selectedIndex) {
                    item.classList.add('bg-[var(--color-surface-hover)]');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('bg-[var(--color-surface-hover)]');
                }
            });
        }

        input.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            selectedIndex = -1;
            
            if (!query) {
                // Show everything
                items.forEach(item => {
                    item.style.display = '';
                    item.classList.remove('bg-[var(--color-surface-hover)]');
                });
                headers.forEach(header => header.style.display = '');
                return;
            }

            // Hide headers during search for cleaner look
            headers.forEach(header => header.style.display = 'none');

            // Filter items
            items.forEach(item => {
                item.classList.remove('bg-[var(--color-surface-hover)]');
                const text = item.textContent.toLowerCase();
                if (text.includes(query)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Auto-select first visible item
            const visibleItems = items.filter(item => item.style.display !== 'none');
            if (visibleItems.length > 0) {
                selectedIndex = 0;
                updateSelection();
            }
        });
        
        input.addEventListener('keydown', (e) => {
            const visibleItems = items.filter(item => item.style.display !== 'none');
            if (visibleItems.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = (selectedIndex + 1) % visibleItems.length;
                updateSelection();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = (selectedIndex - 1 + visibleItems.length) % visibleItems.length;
                updateSelection();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < visibleItems.length) {
                    visibleItems[selectedIndex].click(); // navigate to link
                }
            }
        });
    }
});

/* Reporting JS Logic */

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

document.addEventListener('DOMContentLoaded', function() {
    const scheduleForm = document.getElementById('scheduleForm');
    if (scheduleForm) {
        scheduleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(scheduleForm);
            const data = Object.fromEntries(formData.entries());
            
            fetch('/reports/schedule/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    window.Toast.show(data.message, 'success');
                    document.getElementById('scheduleModal').classList.add('hidden');
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    window.Toast.show(data.message, 'error');
                }
            });
        });
    }
});

function toggleSchedule(id) {
    fetch(`/reports/schedule/${id}/toggle/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken')}
    }).then(res => res.json()).then(data => {
        window.Toast.show(data.message, data.status);
        setTimeout(() => window.location.reload(), 1000);
    });
}

function runSchedule(id) {
    fetch(`/reports/schedule/${id}/run/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken')}
    }).then(res => res.json()).then(data => {
        window.Toast.show(data.message, data.status);
    });
}

function deleteSchedule(id) {
    if(confirm("Are you sure you want to delete this scheduled report?")) {
        fetch(`/reports/schedule/${id}/delete/`, {
            method: 'DELETE',
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(res => res.json()).then(data => {
            window.Toast.show(data.message, data.status);
            setTimeout(() => window.location.reload(), 1000);
        });
    }
}

function generatePreview() {
    document.getElementById('cr-step-2').classList.add('hidden');
    document.getElementById('cr-step-3').classList.remove('hidden');
    
    const source = document.getElementById('cr-source').value;
    const status = document.getElementById('cr-status').value;
    const days = document.getElementById('cr-days').value;
    
    fetch('/reports/custom/preview/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({source: source, filters: {status: status, date_range: days}})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('cr-preview-area').innerHTML = `
            <div class="font-bold text-lg mb-2">Total Records Found: ${data.total_records}</div>
            <div class="text-[var(--color-muted)]">${data.sample_data}</div>
        `;
    });
}

function submitCustomExport(format) {
    const source = document.getElementById('cr-source').value;
    const status = document.getElementById('cr-status').value;
    const days = document.getElementById('cr-days').value;
    window.location.href = `/reports/export/?source=${source}&status=${status}&date_range=${days}&format=${format}`;
    window.Toast.show('Generating export...', 'info');
    document.getElementById('customReportModal').classList.add('hidden');
}
