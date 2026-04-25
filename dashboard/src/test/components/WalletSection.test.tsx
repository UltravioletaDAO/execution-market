// WalletSection tests — ADR-001 wallet surface on /profile.
// Covers: render states (loading/loaded/error), totals math, action enablement,
// and modal open/close wiring. Dynamic SDK + useOnchainBalance are mocked so
// tests are deterministic and don't hit RPCs.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WalletSection } from '../../components/profile/wallet/WalletSection'
import type { ChainBalance } from '../../hooks/useOnchainBalance'
import { NETWORK_BY_KEY } from '../../config/networks'

const mockRefetch = vi.fn()
const mockHookReturn = {
  balances: [] as ChainBalance[],
  totalUsdc: 0,
  loading: false,
  error: null as Error | null,
  lastUpdated: null as Date | null,
  refetch: mockRefetch,
}

vi.mock('../../hooks/useOnchainBalance', () => ({
  useOnchainBalance: () => mockHookReturn,
}))

vi.mock('@dynamic-labs/sdk-react-core', () => ({
  useDynamicContext: () => ({
    primaryWallet: {
      address: '0xabc123',
      connector: { isEmbeddedWallet: true },
    },
    setShowDynamicUserProfile: vi.fn(),
  }),
}))

vi.mock('qrcode', () => ({
  default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,abc') },
}))

const TEST_ADDRESS = '0x1234567890abcdef1234567890abcdef12345678'

describe('WalletSection', () => {
  beforeEach(() => {
    mockHookReturn.balances = []
    mockHookReturn.totalUsdc = 0
    mockHookReturn.loading = false
    mockHookReturn.error = null
    mockHookReturn.lastUpdated = null
    mockRefetch.mockClear()
  })

  it('renders header with shortened wallet address', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText(/0x1234/)).toBeTruthy()
    expect(screen.getByText(/5678/)).toBeTruthy()
  })

  it('shows total USDC = $0.00 when no balances', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText('$0.00')).toBeTruthy()
  })

  it('disables Send when totalUsdc is zero', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const sendButton = screen.getByRole('button', { name: /Send/i })
    expect((sendButton as HTMLButtonElement).disabled).toBe(true)
  })

  it('enables Send when worker has balance on some chain', () => {
    mockHookReturn.totalUsdc = 12.34
    mockHookReturn.balances = [
      { network: NETWORK_BY_KEY.base, balance: 12.34, raw: 12340000n, error: null, loading: false },
    ]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const sendButton = screen.getByRole('button', { name: /Send/i })
    expect((sendButton as HTMLButtonElement).disabled).toBe(false)
    // $12.34 appears twice: hero total + per-chain row
    expect(screen.getAllByText('$12.34').length).toBeGreaterThanOrEqual(2)
  })

  it('renders per-chain breakdown with balances', () => {
    mockHookReturn.totalUsdc = 5.5
    mockHookReturn.balances = [
      { network: NETWORK_BY_KEY.base, balance: 3.0, raw: 3000000n, error: null, loading: false },
      { network: NETWORK_BY_KEY.polygon, balance: 2.5, raw: 2500000n, error: null, loading: false },
    ]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText('$3.00')).toBeTruthy()
    expect(screen.getByText('$2.50')).toBeTruthy()
    expect(screen.getByText('Base')).toBeTruthy()
    expect(screen.getByText('Polygon')).toBeTruthy()
  })

  it('shows RPC error pill when a chain fails but keeps others', () => {
    mockHookReturn.totalUsdc = 3.0
    mockHookReturn.balances = [
      { network: NETWORK_BY_KEY.base, balance: 0, raw: 0n, error: 'RPC timeout', loading: false },
      { network: NETWORK_BY_KEY.polygon, balance: 3.0, raw: 3000000n, error: null, loading: false },
    ]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText(/RPC error/i)).toBeTruthy()
    // Polygon row still renders its balance despite Base RPC failure
    expect(screen.getByText('Polygon')).toBeTruthy()
  })

  it('shows top-level error banner when hook returns error', () => {
    mockHookReturn.error = new Error('Network unreachable')
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText(/Network unreachable/i)).toBeTruthy()
  })

  it('refetch is invoked when refresh button clicked', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const refreshBtn = screen.getByLabelText(/Refresh/i)
    fireEvent.click(refreshBtn)
    expect(mockRefetch).toHaveBeenCalledTimes(1)
  })

  it('opens Receive modal when Receive clicked', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const receiveBtn = screen.getByRole('button', { name: /Receive/i })
    fireEvent.click(receiveBtn)
    // Modal-only text that isn't in WalletSection itself
    expect(screen.getByText(/Your wallet address/i)).toBeTruthy()
    expect(screen.getByText(/One address, multiple chains/i)).toBeTruthy()
  })

  it('opens Send modal when Send clicked and worker has balance', () => {
    mockHookReturn.totalUsdc = 10
    mockHookReturn.balances = [
      { network: NETWORK_BY_KEY.base, balance: 10, raw: 10000000n, error: null, loading: false },
    ]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const sendBtn = screen.getByRole('button', { name: /Send/i })
    fireEvent.click(sendBtn)
    // Modal-only text that isn't already in WalletSection
    expect(screen.getByText(/Recipient address/i)).toBeTruthy()
    expect(screen.getByText(/Amount \(USDC\)/i)).toBeTruthy()
  })

  it('renders export button for embedded wallets', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText(/Export your private key/i)).toBeTruthy()
  })
})
