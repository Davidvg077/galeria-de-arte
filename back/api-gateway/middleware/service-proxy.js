const { createProxyMiddleware } = require('http-proxy-middleware');

function serviceProxy(target, prefix) {
  return createProxyMiddleware({
    target,
    changeOrigin: true,
    pathRewrite: (path) => `${prefix}${path === '/' ? '' : path.startsWith('/?') ? path.slice(1) : path}`,
  });
}

module.exports = serviceProxy;
