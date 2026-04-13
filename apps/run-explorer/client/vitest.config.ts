import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'
const __dirname = dirname(fileURLToPath(import.meta.url))
export default defineConfig({
  plugins: [vue()],
  test: { environment: 'jsdom', globals: true },
  resolve: { alias: { '@': resolve(__dirname, './src'), '@shared': resolve(__dirname, '../shared') } }
})
