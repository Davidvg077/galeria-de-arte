const { serviceUrl } = require('../config/service-urls');
const serviceProxy = require('../middleware/service-proxy');

function registerApiRoutes(app) {
  app.use('/api/galleries', serviceProxy(serviceUrl('GALLERY_SERVICE_URL', 'http://localhost:3001'), '/api/galleries'));
  app.use('/api/galerias', serviceProxy(serviceUrl('GALLERY_SERVICE_URL', 'http://localhost:3001'), '/api/galerias'));
  app.use('/api/works', serviceProxy(serviceUrl('WORKS_SERVICE_URL', 'http://localhost:3002'), '/api/works'));
  app.use('/api/auth', serviceProxy(serviceUrl('AUTH_SERVICE_URL', 'http://localhost:3003'), '/api/auth'));
  app.use('/api/purchases', serviceProxy(serviceUrl('PURCHASE_SERVICE_URL', 'http://localhost:3004'), '/api/purchases'));
  app.use('/api/cart', serviceProxy(serviceUrl('PURCHASE_SERVICE_URL', 'http://localhost:3004'), '/api/cart'));
  app.use('/api/content', serviceProxy(serviceUrl('CONTENT_SERVICE_URL', 'http://localhost:3005'), '/api/content'));
  app.use('/api/artists', serviceProxy(serviceUrl('CONTENT_SERVICE_URL', 'http://localhost:3005'), '/api/artists'));
}

module.exports = registerApiRoutes;
