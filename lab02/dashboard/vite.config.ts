import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'serve-lab02-dados',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && (req.url.startsWith('/dados/') || req.url.startsWith('/lab02/dados/'))) {
            const fileName = path.basename(req.url.split('?')[0]);
            const filePath = path.resolve(__dirname, '../dados', fileName);
            if (fs.existsSync(filePath)) {
              res.setHeader('Content-Type', 'text/csv; charset=utf-8');
              return fs.createReadStream(filePath).pipe(res);
            }
          }
          next();
        });
      },
    },
  ],
  base: './',
  server: {
    port: 5174,
    fs: {
      allow: ['..'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
