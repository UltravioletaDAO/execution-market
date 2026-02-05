import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Initialize i18n (must be imported before App)
import './i18n'

// Dynamic.xyz provider for wallet auth
import { DynamicProvider } from './providers/DynamicProvider'

import App from './App'
import './index.css'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <DynamicProvider>
        <App />
      </DynamicProvider>
    </QueryClientProvider>
  </StrictMode>,
)
