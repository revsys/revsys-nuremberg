import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/static/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    ourDir: path.resolve(__dirname, './static'),
    assetsDir: '',
    manifest: true,
    emptyOutDir: true,
    target: 'es2015',
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, './src/main.jsx'),
        author: path.resolve(__dirname, './src/authorHover.jsx'),
      },
      output: {
        chunkFileNames: undefined,
      },
    }
  }
})
