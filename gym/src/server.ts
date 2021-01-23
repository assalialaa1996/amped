import sirv from 'sirv';
import polka from 'polka';
import compression from 'compression';
import { v4 as uuidv4 } from 'uuid';
import * as sapper from '@sapper/server';

const { PORT, NODE_ENV } = process.env;
const dev = NODE_ENV === 'development';

polka() // You can also use Express
  .use((req, res, next) => {
    res.locals = {};
    res.locals.nonce = uuidv4();
    next();
  })
  .use(
    compression({ threshold: 0 }),
    sirv('static', { dev }),
    sapper.middleware()
  )
  .listen(PORT, (err) => {
    if (err) console.log('error', err);
  });
