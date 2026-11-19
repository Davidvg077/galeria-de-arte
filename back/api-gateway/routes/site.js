const express = require('express');
const path = require('path');

function registerSiteRoutes(app) {
  const frontendDirectory = path.join(__dirname, '..', '..', '..', 'front', 'dist');
  app.get('/health', (_req, res) => {
    res.json({ service: 'api-gateway', status: 'ok' });
  });
  app.use(express.static(frontendDirectory));
  app.use((req, res, next) => {
    if (req.method !== 'GET' || req.path.startsWith('/api/')) {
      next();
      return;
    }
    res.sendFile(path.join(frontendDirectory, 'index.html'), (error) => {
      if (error) next(error);
    });
  });
}

module.exports = registerSiteRoutes;
