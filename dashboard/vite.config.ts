/// <reference types="vitest" />
// Dashboard build — execution.market SPA
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { writeFileSync, mkdirSync } from 'fs'
import { resolve } from 'path'

/**
 * Vite plugin: writes version.json into dist/ at build time.
 * CI sets VITE_GIT_SHA and VITE_BUILD_TIMESTAMP; local builds fall back to "dev".
 */
function versionJsonPlugin() {
  return {
    name: 'version-json',
    closeBundle() {
      const gitSha = process.env.VITE_GIT_SHA || 'dev'
      const buildTs = process.env.VITE_BUILD_TIMESTAMP || new Date().toISOString()
      const data = {
        version: buildTs,
        git_sha: gitSha,
        git_sha_short: gitSha.slice(0, 7),
        component: 'dashboard',
        build_timestamp: buildTs,
      }
      const outDir = resolve(__dirname, 'dist')
      mkdirSync(outDir, { recursive: true })
      writeFileSync(resolve(outDir, 'version.json'), JSON.stringify(data, null, 2))
    },
  }
}

export default defineConfig({
  plugins: [react(), versionJsonPlugin()],
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'dist',
    // Phase 0 GR-0.5 / FE-013: sourcemaps disabled in production builds.
    // Sourcemaps make reverse-engineering trivial and can leak internal
    // module paths. Keep false for any shipped build. If a developer
    // needs sourcemaps locally, override with `vite build --sourcemap`.
    sourcemap: false,
    // The vendor-web3 chunk (~5MB) contains @dynamic-labs + @walletconnect +
    // @reown + viem + wagmi. These libraries are deeply intertwined and cannot
    // be split further. The chunk is lazy-loaded via DynamicProvider so it
    // doesn't block initial render. All app code chunks are well under 200KB.
    chunkSizeWarningLimit: 6000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          // React core
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
            return 'vendor-react'
          }
          // React Router
          if (id.includes('node_modules/react-router') || id.includes('node_modules/@remix-run/router')) {
            return 'vendor-router'
          }
          // TanStack React Query
          if (id.includes('node_modules/@tanstack/')) {
            return 'vendor-query'
          }
          // Web3 auth stack: Dynamic SDK + WalletConnect + Reown + viem + wagmi
          // These libraries have deep circular dependencies between them.
          // They must be in one chunk to avoid Rollup circular-chunk warnings.
          // The combined chunk is large (~5MB) but is lazy-loaded via DynamicProvider.
          if (
            id.includes('node_modules/@dynamic-labs/') ||
            id.includes('node_modules/@walletconnect/') ||
            id.includes('node_modules/@web3modal/') ||
            id.includes('node_modules/@reown/') ||
            id.includes('node_modules/viem/') ||
            id.includes('node_modules/ox/') ||
            id.includes('node_modules/wagmi/') ||
            id.includes('node_modules/@wagmi/')
          ) {
            return 'vendor-web3'
          }
          // Charts
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3-')) {
            return 'vendor-charts'
          }
          // Maps
          if (id.includes('node_modules/leaflet') || id.includes('node_modules/react-leaflet')) {
            return 'vendor-maps'
          }
          // i18n
          if (id.includes('node_modules/i18next') || id.includes('node_modules/react-i18next')) {
            return 'vendor-i18n'
          }
          // Supabase
          if (id.includes('node_modules/@supabase/')) {
            return 'vendor-supabase'
          }
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    include: [
      'src/**/*.test.{ts,tsx}',
      'src/**/*.spec.{ts,tsx}',
    ],
    exclude: [
      'node_modules/**',
      'e2e/**',
      '**/*.e2e.{ts,tsx,js,jsx}',
      '**/playwright/**',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        'dist/',
      ],
    },
  },
})
