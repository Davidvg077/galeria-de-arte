const { test, expect } = require('@playwright/test');

test('Inicio: muestra GART Gallery y la navegación principal', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle(/GART Gallery/);
  await expect(page.locator('header .brand')).toContainText('GART');
  await expect(page.getByRole('navigation', { name: 'Navegación principal' })).toBeVisible();
});

test('Obras: muestra la página y contenido del catálogo', async ({ page }) => {
  await page.route('**/api/works**', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      items: [{ id: 1, title: 'Obra de prueba', category: 'Pintura', year: 2026, price: 100000 }],
    }),
  }));

  await page.goto('/works/');

  await expect(page.getByRole('heading', { name: 'Obras seleccionadas' })).toBeVisible();
  await expect(page.locator('#works-list .work-tile')).toContainText('Obra de prueba');
});

test('Artistas: carga la página y muestra su contenido', async ({ page }) => {
  await page.route('**/api/artists', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ items: [{ id: 1, name: 'Artista de prueba', biography: 'Biografía de prueba.' }] }),
  }));

  await page.goto('/artists/');

  await expect(page.getByRole('heading', { name: 'Artistas', exact: true })).toBeVisible();
  await expect(page.locator('#artist-list')).toContainText('Artista de prueba');
});

test('Contacto: muestra la sección de contacto', async ({ page }) => {
  await page.goto('/contact/');

  await expect(page.getByRole('heading', { name: 'Contacto', exact: true })).toBeVisible();
});

test('Login inválido: muestra un error y permanece en login', async ({ page }) => {
  await page.route('**/api/auth/login', (route) => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Credenciales inválidas.' }),
  }));

  await page.goto('/login/');
  await page.locator('#login-form').getByLabel('Usuario').fill('usuario-invalido-e2e');
  await page.locator('#login-form').getByLabel('Contraseña').fill('clave-invalida-e2e');
  await page.getByRole('button', { name: 'Iniciar sesión' }).last().click();

  await expect(page).toHaveURL(/\/login\/?$/);
  await expect(page.locator('#auth-status')).toContainText('Credenciales inválidas');
});

test('Registro: explica que el usuario no puede ser un correo', async ({ page }) => {
  await page.route('**/api/auth/register', (route) => route.fulfill({
    status: 422,
    contentType: 'application/json',
    body: JSON.stringify({ detail: [{ loc: ['body', 'username'], msg: 'Value error, Usa el campo «Correo electrónico»' }] }),
  }));

  await page.goto('/login/');
  await page.getByRole('button', { name: 'Registrarse' }).click();
  await page.locator('#register-form').getByLabel('Usuario').fill('persona@example.com');
  await page.locator('#register-form').getByLabel('Correo electrónico').fill('persona@example.com');
  await page.locator('#register-form').getByLabel('Teléfono internacional').fill('+573001234567');
  await page.locator('#register-form').getByLabel('Contraseña', { exact: true }).fill('clave-larga-123!');
  await page.locator('#register-form').getByLabel('Confirmar contraseña').fill('clave-larga-123!');

  await expect(page.locator('#register-form')).toContainText('Ejemplo válido');
  await page.locator('#register-form').getByRole('button', { name: 'Crear cuenta' }).click();

  await expect(page.locator('#auth-status')).toContainText('campo «Correo electrónico»');
});

test('Perfil: cambia el rol en ambas direcciones en escritorio y móvil', async ({ page }) => {
  let role = 'VISITANTE';
  await page.route('**/api/auth/me', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      authenticated: true,
      user: {
        id: 77,
        username: 'visitante_e2e',
        email: 'visitante@example.com',
        phone: '+573001234567',
        email_verified: true,
        phone_verified: true,
        role,
        permissions: role === 'ARTISTA' ? ['works:read', 'works:submit'] : ['works:read'],
      },
    }),
  }));
  await page.route('**/api/auth/role/toggle', (route) => {
    role = role === 'VISITANTE' ? 'ARTISTA' : 'VISITANTE';
    return route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        user: {
          id: 77,
          username: 'visitante_e2e',
          email: 'visitante@example.com',
          phone: '+573001234567',
          email_verified: true,
          phone_verified: true,
          role,
          permissions: role === 'ARTISTA' ? ['works:read', 'works:submit'] : ['works:read'],
        },
      }),
    });
  });

  await page.goto('/profile/');
  await expect(page.locator('.profile-role')).toContainText('Visitante');
  await page.getByRole('button', { name: 'Cambiar a artista' }).click();
  await expect(page.locator('.profile-role')).toContainText('Artista');
  await page.getByRole('button', { name: 'Cambiar a visitante' }).click();
  await expect(page.locator('.profile-role')).toContainText('Visitante');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole('button', { name: 'Cambiar a artista' })).toBeVisible();
});

test('Compra: evita doble ejecución y conserva el carrito ante fallo', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ authenticated: true, user: { id: 88, username: 'comprador', role: 'VISITANTE', email_verified: true } }),
  }));
  await page.route('**/api/works/1', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ id: 1, title: 'Obra de prueba', price: 125000, available: true, image_url: '' }),
  }));
  let checkoutCalls = 0;
  await page.route('**/api/purchases/checkout', (route) => {
    checkoutCalls += 1;
    return route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'checkout-e2e', total: 125000, status: 'pending_confirmation', expires_at: '2099-01-01T00:00:00Z', demo_code: '042391' }),
    });
  });

  await page.addInitScript(() => localStorage.setItem('gart.cart', JSON.stringify([{ work_id: 1, quantity: 1 }])));
  await page.goto('/cart/');
  await expect(page.getByRole('heading', { name: 'Obra de prueba' })).toBeVisible();
  await page.getByRole('button', { name: 'Finalizar compra' }).dblclick();
  await expect(page.locator('#confirmation-form')).toBeVisible();
  await expect(page.locator('#cart-status')).toContainText('125.000');
  await expect.poll(() => checkoutCalls).toBe(1);

  await page.route('**/api/purchases/checkout-e2e/confirm', (route) => route.fulfill({
    status: 500,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'No se pudo guardar el pedido. Inténtalo de nuevo.' }),
  }));
  await page.locator('#checkout-code').fill('042391');
  await page.locator('#confirmation-form').getByRole('button', { name: 'Confirmar pedido' }).click();
  await expect(page.locator('#cart-status')).toContainText('No se pudo guardar');
  await expect(page.locator('#cart-status')).toBeVisible();
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('gart.cart') || '[]').length)).toBe(1);
});

test('Menú móvil: permite acceder a las secciones principales', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  await page.getByRole('button', { name: 'Abrir menú' }).click();

  const mobileNavigation = page.getByRole('navigation', { name: 'Navegación móvil' });
  await expect(mobileNavigation).toBeVisible();
  for (const section of ['Inicio', 'Galerías', 'Artistas', 'Obras', 'Sobre nosotros', 'Contacto']) {
    await expect(mobileNavigation.getByRole('link', { name: section, exact: true })).toBeVisible();
  }
});