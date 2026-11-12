import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'serve-lab04-dados',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && (req.url.startsWith('/dados/') || req.url.startsWith('/lab04/dados/'))) {
            const relativePart = req.url.split('?')[0].replace(/^\/(?:lab04\/)?dados\//, '');
            const candidatePaths = [
              path.resolve(__dirname, '../dados', relativePart),
              path.resolve(__dirname, '../dados/reais', relativePart),
              path.resolve(__dirname, '../dados/simulado', relativePart),
            ];

            for (const filePath of candidatePaths) {
              if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
                if (filePath.endsWith('.json')) {
                  res.setHeader('Content-Type', 'application/json; charset=utf-8');
                } else if (filePath.endsWith('.csv')) {
                  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
                }
                return fs.createReadStream(filePath).pipe(res);
              }
            }
          }
          next();
        });
      },
    },
  ],
  base: './',
  server: {
    port: 5176,
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
