const express = require('express');
const forwardedHeaders = require('./middleware/forwarded-headers');
const registerApiRoutes = require('./routes/api');
const registerSiteRoutes = require('./routes/site');

const app = express();
const PORT = Number(process.env.PORT) || 3000;

if (process.env.NODE_ENV === 'production') {
  app.set('trust proxy', 1);
}

app.use(forwardedHeaders);
registerApiRoutes(app);
registerSiteRoutes(app);

app.listen(PORT, () => {
  console.log(`GART Gallery en el puerto ${PORT}`);
});
