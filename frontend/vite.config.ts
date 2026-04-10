import { execSync } from 'node:child_process'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

/** Same default as backend/run_dev_wsl.sh (avoid busy :8000). */
const DEFAULT_POC_API_PORT = '8787'

/**
 * Dev proxy for /api:
 * - VITE_PROXY_API=http://host:port — full base URL (highest priority)
 * - VITE_USE_WSL_API=true — Windows: pick WSL LAN IP + VITE_API_PORT (default 8787)
 * - default: http://127.0.0.1:8787
 */
function resolveApiTarget(env: Record<string, string>): string {
  if (env.VITE_PROXY_API?.trim()) {
    return env.VITE_PROXY_API.trim()
  }
  const apiPort = env.VITE_API_PORT?.trim() || DEFAULT_POC_API_PORT
  const localhost = `http://127.0.0.1:${apiPort}`

  const wslFlag = (env.VITE_USE_WSL_API || '').trim().toLowerCase()
  if (wslFlag === 'false' || wslFlag === '0') {
    return localhost
  }
  const useWsl = wslFlag === '1' || wslFlag === 'true'
  if (useWsl && process.platform === 'win32') {
    try {
      const out = execSync('wsl -e hostname -I', {
        encoding: 'utf-8',
        timeout: 8000,
        windowsHide: true,
      }).trim()
      const ips = out.split(/\s+/).filter(Boolean)
      const ip =
        ips.find((a) => a.startsWith('192.168.')) ||
        ips.find((a) => /^10\./.test(a) && !a.startsWith('10.255.')) ||
        ips[0]
      if (ip) {
        const url = `http://${ip}:${apiPort}`
        console.info(`[vite] VITE_USE_WSL_API: /api → ${url}`)
        return url
      }
    } catch (e) {
      console.warn(`[vite] VITE_USE_WSL_API failed; using ${localhost}. Is WSL installed?`, e)
    }
  }
  return localhost
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = resolveApiTarget(env)

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          // Long runs (video → Gemini) + SSE: avoid proxy closing early
          timeout: 600_000,
          proxyTimeout: 600_000,
        },
      },
    },
  }
})
