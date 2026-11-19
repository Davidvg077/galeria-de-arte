function serviceUrl(name, fallback) {
  const url = process.env[name] || fallback;
  return /^[a-z][a-z\d+.-]*:\/\//i.test(url) ? url : `http://${url}`;
}

module.exports = { serviceUrl };
