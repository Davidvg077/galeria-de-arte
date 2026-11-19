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
  const dashboardLink = document.querySelector('[data-dashboard-link]');
  if (!authLink) return;

  authLink.addEventListener('click', async (event) => {
    if (authLink.textContent !== 'Cerrar sesión') return;
    event.preventDefault();
    authLink.setAttribute('aria-busy', 'true');
    try {
      await logout();
      window.location.assign('/login');
    } catch (error) {
      console.error('No se pudo cerrar la sesión.', error);
      window.alert('No se pudo cerrar la sesión. Comprueba tu conexión e inténtalo de nuevo.');
    } finally {
      authLink.removeAttribute('aria-busy');
    }
  });

  getCurrentUser()
    .then((user) => {
      if (!user) return;
      authLink.textContent = 'Cerrar sesión';
      authLink.href = '/login';
      authLink.setAttribute('aria-label', `Cerrar sesión de ${user.username}`);
      if (dashboardLink && ['ARTISTA', 'WEBMASTER'].includes(user.role)) {
        dashboardLink.href = user.role === 'WEBMASTER' ? '/dashboard' : '/artist/dashboard';
        dashboardLink.textContent = user.role === 'WEBMASTER' ? 'Administración' : 'Mi espacio';
        dashboardLink.hidden = false;
      }
    })
    .catch((error) => console.error('No se pudo validar la sesión.', error));
}
