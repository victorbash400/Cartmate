import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': '/src',
      '@/components': '/src/components',
      '@/services': '/src/services',
      '@/types': '/src/types',
      '@/hooks': '/src/hooks',
      '@/context': '/src/context',
      '@/utils': '/src/utils',
      '@/data': '/src/data',
    },
  },
})
