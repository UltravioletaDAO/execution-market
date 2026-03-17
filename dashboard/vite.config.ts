/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// @xmtp/browser-sdk is not installed as an npm dependency — it's used via
// dynamic import() inside a try/catch in XMTPContext.tsx.  This plugin
// resolves it to a shim that throws at runtime so the catch block handles it.
function xmtpStubPlugin(): Plugin {
  const STUB_ID = '\0xmtp-stub';
  return {
    name: 'xmtp-stub',
    resolveId(source) {
      if (source === '@xmtp/browser-sdk') return STUB_ID;
      return null;
    },
    load(id) {
      if (id === STUB_ID) return 'throw new Error("@xmtp/browser-sdk not available");';
      return null;
    },
  };
}

export default defineConfig({
  plugins: [react(), xmtpStubPlugin()],
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
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
