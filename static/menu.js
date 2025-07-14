// Toggle the menu visibility
function toggleMenu() {
  const menu = document.getElementById('menu');
  const overlay = document.getElementById('overlay');
  const burger = document.getElementById('burger');
  const isOpen = menu?.classList.contains('open');

  if (isOpen) {
    closeMenu();
  } else {
    menu.classList.add('open');
    overlay.classList.add('active');
    burger.classList.add('open');

    // Register event listener only when menu opens
    document.addEventListener('click', handleOutsideClick);
  }
}

// Close menu on outside click
function handleOutsideClick(event) {
  const navigation = document.getElementById('navigation');

  if (!navigation?.contains(event.target)) {
    closeMenu();
  }
}

// Close menu and de-register event listener
function closeMenu() {
  const menu = document.getElementById('menu');
  const overlay = document.getElementById('overlay');
  const burger = document.getElementById('burger');

  menu.classList.remove('open');
  overlay.classList.remove('active');
  burger.classList.remove('open');

  // Remove event listener when menu closes
  document.removeEventListener('click', handleOutsideClick);
}

// Prevent menu from staying open on back/forward navigation
window.addEventListener('pageshow', () => {
  closeMenu(true); // true = skip animation
});

// Optional: if you use history.pushState or have SPA behavior
window.addEventListener('popstate', () => {
  closeMenu(true); // true = skip animation
});
