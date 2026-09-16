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
});
