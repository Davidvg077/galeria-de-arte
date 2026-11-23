const apiGatewayUrl = import.meta.env.PUBLIC_API_GATEWAY_URL || (import.meta.env.DEV ? 'http://localhost:3000' : '');

export async function getCurrentUser() {
  const response = await fetch(`${apiGatewayUrl}/api/auth/me`, { credentials: 'include' });
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new Error(`No se pudo validar la sesión (${response.status}).`);
  }

  const session = await response.json();
  return session.authenticated ? session.user : null;
}

export async function logout() {
  const response = await fetch(`${apiGatewayUrl}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(`No se pudo cerrar la sesión (${response.status}).`);
  }
}

export function initializeAuthNavigation() {
  const authLink = document.querySelector('[data-auth-link]');
  const accountMenu = document.querySelector('[data-account-menu]');
  const accountToggle = document.querySelector('.account-toggle');
  const accountDropdown = document.querySelector('.account-dropdown');
  const usernameLabel = document.querySelector('[data-account-username]');
  const logoutButton = document.querySelector('[data-logout-link]');
  const dashboardLink = document.querySelector('[data-dashboard-link]');
  if (!authLink) return;

  const setAccountMenuOpen = (open, restoreFocus = false) => {
    if (!accountDropdown || !accountToggle) return;
    accountDropdown.hidden = !open;
    accountToggle.setAttribute('aria-expanded', String(open));
    if (!open && restoreFocus) accountToggle.focus();
  };

  accountToggle?.addEventListener('click', () => {
    setAccountMenuOpen(accountDropdown?.hidden ?? true);
  });
  document.addEventListener('click', (event) => {
    if (accountMenu && !accountMenu.contains(event.target)) setAccountMenuOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && accountDropdown && !accountDropdown.hidden) {
      setAccountMenuOpen(false, true);
    }
  });
  accountDropdown?.querySelector('a')?.addEventListener('click', () => setAccountMenuOpen(false));

  logoutButton?.addEventListener('click', async () => {
    logoutButton.setAttribute('aria-busy', 'true');
    try {
      await logout();
      window.location.assign('/login');
    } catch (error) {
      console.error('No se pudo cerrar la sesión.', error);
      window.alert('No se pudo cerrar la sesión. Comprueba tu conexión e inténtalo de nuevo.');
    } finally {
      logoutButton.removeAttribute('aria-busy');
    }
  });

  getCurrentUser()
    .then((user) => {
      if (!user) return;
      authLink.hidden = true;
      if (accountMenu && accountToggle && usernameLabel) {
        usernameLabel.textContent = user.username;
        accountToggle.setAttribute('aria-label', `${user.username}, abrir menú de usuario`);
        accountMenu.hidden = false;
      }
      if (dashboardLink && ['ARTISTA', 'WEBMASTER'].includes(user.role)) {
        dashboardLink.href = user.role === 'WEBMASTER' ? '/dashboard' : '/artist/dashboard';
        dashboardLink.textContent = user.role === 'WEBMASTER' ? 'Administración' : 'Mi espacio';
        dashboardLink.hidden = false;
      }
    })
    .catch((error) => console.error('No se pudo validar la sesión.', error));
}
