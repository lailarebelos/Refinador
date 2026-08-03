import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Apenas /api vai para o backend FastAPI.
      // /brand é servido diretamente pelo Vite de frontend/public/brand/ —
      // NÃO adicione /brand aqui ou o proxy intercepta antes do static serving.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
