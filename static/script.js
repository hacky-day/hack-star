// Load reusable menu
window.addEventListener('DOMContentLoaded', async () => {
    const menuContainer = document.getElementById('menu-container');
    if (menuContainer) {
        const res = await fetch('menu.html');
        const html = await res.text();
        menuContainer.innerHTML = html;
    }
});

// Toggle the menu visibility
function toggleMenu() {
    const menu = document.getElementById('menu');
    const overlay = document.getElementById('overlay');
    const burger = document.querySelector('.burger');
    const isOpen = menu?.classList.contains('open');

    if (isOpen) {
        menu.classList.remove('open');
        overlay.classList.remove('active');
        burger?.classList.remove('open');
    } else {
        menu.classList.add('open');
        overlay.classList.add('active');
        burger?.classList.add('open');
    }
}

// Close menu on outside click
document.addEventListener('click', function (event) {
    const burger = document.querySelector('.burger');
    const menu = document.getElementById('menu');
    const overlay = document.getElementById('overlay');

    if (
        !burger?.contains(event.target) &&
        !menu?.contains(event.target) &&
        !overlay?.contains(event.target)
    ) {
        menu?.classList.remove('open');
        overlay?.classList.remove('active');
    }
});
