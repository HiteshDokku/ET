import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// Plugin to dynamically scan frame files at build time
function frameListPlugin() {
  const virtualId = 'virtual:frame-list'
  const resolvedId = '\0' + virtualId

  return {
    name: 'frame-list',
    resolveId(id) {
      if (id === virtualId) return resolvedId
    },
    load(id) {
      if (id === resolvedId) {
        const dir = path.resolve(process.cwd(), 'public/et_frames')
        const files = fs.readdirSync(dir)
          .filter(f => /^frame_\d+.*\.gif$/.test(f))
          .sort((a, b) => {
            const na = parseInt(a.match(/frame_(\d+)/)[1])
            const nb = parseInt(b.match(/frame_(\d+)/)[1])
            return na - nb
          })
        const urls = files.map(f => `/et_frames/${f}`)
        return `export default ${JSON.stringify(urls)};`
      }
    }
  }
}

export default defineConfig({
  plugins: [react(), frameListPlugin()],
})
