function toggleMenu() {
    const menu = document.getElementById('menu');
    const overlay = document.getElementById('overlay');
    const isOpen = menu.classList.contains('open');

    if (isOpen) {
        menu.classList.remove('open');
        overlay.classList.remove('active');
    } else {
        menu.classList.add('open');
        overlay.classList.add('active');
    }
}

// Optional: Close menu when clicking outside
document.addEventListener('click', function (event) {
    const burger = document.querySelector('.burger');
    const menu = document.getElementById('menu');
    const overlay = document.getElementById('overlay');

    if (
        !burger.contains(event.target) &&
        !menu.contains(event.target) &&
        !overlay.contains(event.target)
    ) {
        menu.classList.remove('open');
        overlay.classList.remove('active');
    }
});
