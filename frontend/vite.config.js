import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * vite.config.js
 * ──────────────
 * Vite build configuration.
 *
 * Key settings:
 *  - `@vitejs/plugin-react` enables Fast Refresh (HMR) for React components.
 *  - `server.proxy` forwards /api requests to the FastAPI backend during
 *    development so the browser avoids CORS issues.
 *    In production, Nginx/Caddy would handle this proxy instead.
 *  - `resolve.alias` maps `@` → `./src` so imports can be written as
 *    `import X from '@/components/X'` instead of `'../../components/X'`.
 */
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: { '@': '/src' },
  },

  server: {
    port: 5173,
    proxy: {
      // During development: proxy /api/v1/* → FastAPI at port 8000
      '/api': {
        target:      'http://localhost:8000',
        changeOrigin: true,
        secure:       false,
      },
    },
  },

  build: {
    outDir:        'dist',
    sourcemap:     false,
    chunkSizeWarningLimit: 1000, // recharts is large; suppress warning
  },
});
