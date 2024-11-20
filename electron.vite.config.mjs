import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
  },
  preload: {
    build: {
      rollupOptions: {
        input: {
          chat: resolve(__dirname, 'src/preload/index.js'),
          settings: resolve(__dirname, 'src/preload/index.js')
        }
      }
    }
  },
  renderer: {
    root: './src/renderer',
    build: {
      rollupOptions: {
        input: {
          chat: resolve(__dirname, 'src/renderer/chat/index.html'),
          settings: resolve(__dirname, 'src/renderer/settings/index.html')
        }
      }
    }
  },
})
