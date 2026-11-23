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