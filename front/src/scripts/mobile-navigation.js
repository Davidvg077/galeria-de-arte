export function initializeMobileNavigation() {
  const menuButton = document.querySelector('.mobile-menu-toggle');
  const menu = document.querySelector('.mobile-nav');
  const closeButton = document.querySelector('.mobile-menu-close');
  if (!menuButton || !menu || !closeButton) return;

  const setOpen = (open, restoreFocus = false) => {
    menu.hidden = !open;
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
    if (!open && restoreFocus) menuButton.focus();
  };

  menuButton.addEventListener('click', () => setOpen(menu.hidden));
  closeButton.addEventListener('click', () => setOpen(false, true));
  menu.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setOpen(false));
  });
  document.addEventListener('click', (event) => {
    if (!menu.hidden && !menu.contains(event.target) && !menuButton.contains(event.target)) {
      setOpen(false);
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) setOpen(false, true);
  });
}