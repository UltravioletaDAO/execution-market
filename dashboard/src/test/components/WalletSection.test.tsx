// WalletSection tests — ADR-001 wallet surface on /profile.
// Covers: render states (loading/loaded/error), totals math, action enablement,
// modal open/close wiring, AND the multi-wallet selector. Dynamic SDK +
// useOnchainBalance are mocked so tests are deterministic and don't hit RPCs.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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

interface MockWallet {
  id: string
  address: string
  connector?: { isEmbeddedWallet?: boolean }
}

const mockSwitchWallet = vi.fn().mockResolvedValue(undefined)
const mockSetShowDynamicUserProfile = vi.fn()

const mockDynamicState: {
  primaryWallet: MockWallet | null
  userWallets: MockWallet[]
} = {
  primaryWallet: null,
  userWallets: [],
}

vi.mock('@dynamic-labs/sdk-react-core', () => ({
  useDynamicContext: () => ({
    primaryWallet: mockDynamicState.primaryWallet,
    setShowDynamicUserProfile: mockSetShowDynamicUserProfile,
  }),
  useUserWallets: () => mockDynamicState.userWallets,
  useSwitchWallet: () => mockSwitchWallet,
}))

vi.mock('qrcode', () => ({
  default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,abc') },
}))

const TEST_ADDRESS = '0x1234567890abcdef1234567890abcdef12345678'

const EMBEDDED_WALLET: MockWallet = {
  id: 'wallet-embedded-1',
  address: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  connector: { isEmbeddedWallet: true },
}

const EXTERNAL_WALLET: MockWallet = {
  id: 'wallet-external-1',
  address: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  connector: { isEmbeddedWallet: false },
}

describe('WalletSection', () => {
  beforeEach(() => {
    mockHookReturn.balances = []
    mockHookReturn.totalUsdc = 0
    mockHookReturn.loading = false
    mockHookReturn.error = null
    mockHookReturn.lastUpdated = null
    mockRefetch.mockClear()
    mockSwitchWallet.mockClear()
    mockSetShowDynamicUserProfile.mockClear()
    // Default Dynamic state: primary embedded, no extra wallets — selector hidden
    mockDynamicState.primaryWallet = EMBEDDED_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET]
  })

  it('renders header with shortened wallet address', () => {
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    // Active address comes from primaryWallet (embedded), not the prop
    expect(screen.getByText(/0xaaaa/)).toBeTruthy()
  })

  it('falls back to prop address when Dynamic has no primaryWallet', () => {
    mockDynamicState.primaryWallet = null
    mockDynamicState.userWallets = []
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

  // ---------- WalletSelector ----------

  it('hides selector when only one wallet is linked', () => {
    mockDynamicState.userWallets = [EMBEDDED_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.queryByText(/Active wallet/i)).toBeNull()
    expect(screen.queryByText(/External \(self-custody\)/i)).toBeNull()
  })

  it('shows selector with both wallets when 2+ linked', () => {
    mockDynamicState.primaryWallet = EXTERNAL_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET, EXTERNAL_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    expect(screen.getByText(/Active wallet/i)).toBeTruthy()
    expect(screen.getByText(/Embedded \(Dynamic-managed\)/i)).toBeTruthy()
    expect(screen.getByText(/External \(self-custody\)/i)).toBeTruthy()
  })

  it('marks active wallet with the active badge', () => {
    mockDynamicState.primaryWallet = EXTERNAL_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET, EXTERNAL_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const activeBadges = screen.getAllByText(/^Active$/i)
    // exactly one wallet is active
    expect(activeBadges.length).toBe(1)
  })

  it('clicking a non-active wallet calls switchWallet with the wallet id', async () => {
    mockDynamicState.primaryWallet = EXTERNAL_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET, EXTERNAL_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    // Find the embedded wallet button (not active) by its label text
    const embeddedRow = screen.getByText(/Embedded \(Dynamic-managed\)/i).closest('button')
    expect(embeddedRow).toBeTruthy()
    fireEvent.click(embeddedRow!)
    await waitFor(() => {
      expect(mockSwitchWallet).toHaveBeenCalledWith(EMBEDDED_WALLET.id)
    })
  })

  it('does not call switchWallet when clicking the already-active wallet', () => {
    mockDynamicState.primaryWallet = EXTERNAL_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET, EXTERNAL_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    const externalRow = screen.getByText(/External \(self-custody\)/i).closest('button')
    fireEvent.click(externalRow!)
    expect(mockSwitchWallet).not.toHaveBeenCalled()
  })

  it('uses primaryWallet address for balance display', () => {
    // External primary — balance fetch should target external, not the prop
    mockDynamicState.primaryWallet = EXTERNAL_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET, EXTERNAL_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    // Header + selector both show the shortened external address
    expect(screen.getAllByText(/0xbbbb/).length).toBeGreaterThanOrEqual(1)
    // The TEST_ADDRESS prop is ignored when primaryWallet is set
    expect(screen.queryByText(/0x1234/)).toBeNull()
  })

  it('hides export when active wallet is external', () => {
    mockDynamicState.primaryWallet = EXTERNAL_WALLET
    mockDynamicState.userWallets = [EMBEDDED_WALLET, EXTERNAL_WALLET]
    render(<WalletSection walletAddress={TEST_ADDRESS} />)
    // ExportWalletButton renders the "external wallet" message instead of the export form
    expect(screen.getByText(/external wallet/i)).toBeTruthy()
    expect(screen.queryByText(/Export your private key/i)).toBeNull()
  })
})
