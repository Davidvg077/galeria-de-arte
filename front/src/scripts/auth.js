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
  const accountRole = document.querySelector('[data-account-role]');
  const roleToggleButton = document.querySelector('[data-role-toggle]');
  const roleStatus = document.querySelector('[data-account-role-status]');
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

  const updateRoleMenu = (user) => {
    const canSwitchRole = ['ARTISTA', 'VISITANTE'].includes(user.role);
    if (accountRole) {
      accountRole.textContent = `Rol actual: ${user.role === 'ARTISTA' ? 'Artista' : 'Visitante'}`;
      accountRole.hidden = !canSwitchRole;
    }
    if (roleToggleButton) {
      roleToggleButton.textContent = user.role === 'ARTISTA' ? 'Cambiar a visitante' : 'Cambiar a artista';
      roleToggleButton.hidden = !canSwitchRole;
    }
    if (dashboardLink) {
      const hasDashboard = ['ARTISTA', 'WEBMASTER'].includes(user.role);
      dashboardLink.href = user.role === 'WEBMASTER' ? '/dashboard' : '/artist/dashboard';
      dashboardLink.textContent = user.role === 'WEBMASTER' ? 'Administración' : 'Mi espacio';
      dashboardLink.hidden = !hasDashboard;
    }
  };

  roleToggleButton?.addEventListener('click', async () => {
    roleToggleButton.disabled = true;
    if (roleStatus) roleStatus.textContent = '';
    try {
      const response = await fetch(`${apiGatewayUrl}/api/auth/role/toggle`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail;
        const message = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((item) => item?.msg).filter(Boolean).join(' ')
            : detail && typeof detail === 'object'
              ? detail.message || detail.msg
              : null;
        throw new Error(message || `No se pudo cambiar el rol (${response.status}).`);
      }
      if (!data.user || !['ARTISTA', 'VISITANTE'].includes(data.user.role)) {
        throw new Error('El servidor devolvió un rol no válido.');
      }
      updateRoleMenu(data.user);
      if (roleStatus) {
        roleStatus.textContent = `Rol cambiado a ${data.user.role === 'ARTISTA' ? 'artista' : 'visitante'}.`;
      }
    } catch (error) {
      console.error('No se pudo cambiar el rol.', error);
      if (roleStatus) {
        roleStatus.textContent = error instanceof Error
          ? error.message
          : 'No se pudo cambiar el rol. Comprueba tu conexión e inténtalo de nuevo.';
      }
    } finally {
      roleToggleButton.disabled = false;
    }
  });

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
      updateRoleMenu(user);
    })
    .catch((error) => console.error('No se pudo validar la sesión.', error));
}
