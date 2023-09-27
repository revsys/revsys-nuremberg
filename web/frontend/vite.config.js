import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react({ fastRefresh: false })],
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
        author: path.resolve(__dirname, './src/vanilla/authorHover.js'),
        tool: path.resolve(__dirname, './src/vanilla/toolHover.js'),
        vanillasearch: path.resolve(__dirname, './src/vanilla/search.js'),
        vanillatranscripts: path.resolve(__dirname, './src/vanilla/transcript.js'),
        vanilladocuments: path.resolve(__dirname, './src/vanilla/documents.js'),
      },
      output: {
        chunkFileNames: undefined,
      },
    }
  }
})
