// THEME ENGINE CORE
// Apply theme instantly on Script Load to avoid flash
(function() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark-mode');
    } else {
        document.documentElement.classList.remove('dark-mode');
    }
})();

// Define as a global function for reliability
window.toggleTheme = function() {
    const isDark = document.documentElement.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    
    // Update icons globally
    updateThemeIcons(isDark);
};

function updateThemeIcons(isDark) {
    const icons = document.querySelectorAll('#theme-toggle i');
    icons.forEach(icon => {
        if (isDark) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    });
}

// Initial Sync on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    // If the body doesn't have it but docEl does, sync it (if needed by CSS)
    const isDark = document.documentElement.classList.contains('dark-mode');
    
    // Ensure the body also has it for blanket selectors
    if (isDark) document.body.classList.add('dark-mode');
    
    updateThemeIcons(isDark);
    
    // Bind to button via JS as a backup
    const btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.onclick = window.toggleTheme;
    }
});
