import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Host exacto autorizado para desarrollo remoto. No usar allowedHosts: true.
    // La lista se refiere solo al hostname, sin puerto ni protocolo.
    allowedHosts: ['smarthome.votaya.com.mx'],
    proxy: {
      '/api': { target: process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
