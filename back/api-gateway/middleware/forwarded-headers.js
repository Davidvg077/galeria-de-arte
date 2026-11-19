function forwardedHeaders(req, res, next) {
  req.headers['x-forwarded-host'] = req.get('host');
  req.headers['x-forwarded-proto'] = req.headers['x-forwarded-proto'] || req.protocol;
  req.headers['x-real-ip'] = req.ip;
  const allowedOrigin = process.env.FRONTEND_ORIGIN || process.env.RENDER_EXTERNAL_URL || 'http://localhost:4321';
  res.header('Access-Control-Allow-Origin', allowedOrigin);
  res.header('Access-Control-Allow-Credentials', 'true');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Idempotency-Key');
  res.header('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');
  if (req.method === 'OPTIONS') {
    res.sendStatus(204);
    return;
  }
  next();
}

module.exports = forwardedHeaders;
