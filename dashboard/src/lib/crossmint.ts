/**
 * Crossmint Email Wallet Integration (NOW-042)
 *
 * Enables users to create custodial wallets using just their email address.
 * This removes the barrier of requiring users to install MetaMask or other
 * wallet extensions, making Execution Market accessible to non-crypto-native users.
 *
 * @see https://docs.crossmint.com/wallets/quickstarts/client-side-wallets
 */

// Types for Crossmint SDK (will be properly typed when SDK is installed)
// Using interface definitions for type safety before SDK installation

export interface CrossmintConfig {
  projectId: string;
  environment: 'staging' | 'production';
}

export interface EmailWallet {
  address: string;
  email: string;
  chain: SupportedChain;
  createdAt: Date;
}

export type SupportedChain =
  | 'ethereum'
  | 'base'
  | 'polygon'
  | 'arbitrum'
  | 'optimism';

export interface TransactionRequest {
  to: string;
  value: string;
  data?: string;
  chainId?: number;
}

export interface TransactionResult {
  hash: string;
  status: 'pending' | 'confirmed' | 'failed';
  chainId: number;
}

export interface SignatureResult {
  signature: string;
  message: string;
}

export class CrossmintError extends Error {
  constructor(
    message: string,
    public readonly code: CrossmintErrorCode,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'CrossmintError';
  }
}

export type CrossmintErrorCode =
  | 'NOT_INITIALIZED'
  | 'INVALID_EMAIL'
  | 'WALLET_NOT_FOUND'
  | 'WALLET_CREATION_FAILED'
  | 'TRANSACTION_FAILED'
  | 'SIGNATURE_FAILED'
  | 'NETWORK_ERROR'
  | 'RATE_LIMITED'
  | 'INVALID_CONFIG';

/**
 * Validates email format
 */
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Chain ID mapping for supported chains
 */
const CHAIN_IDS: Record<SupportedChain, number> = {
  ethereum: 1,
  base: 8453,
  polygon: 137,
  arbitrum: 42161,
  optimism: 10,
};

/**
 * Default chain for Execution Market (Base for low fees)
 */
const DEFAULT_CHAIN: SupportedChain = 'base';

/**
 * CrossmintService - Main service for email wallet management
 *
 * Usage:
 * ```typescript
 * import crossmint from '@/lib/crossmint';
 *
 * // Initialize (call once on app start)
 * await crossmint.initialize();
 *
 * // Create wallet for user
 * const wallet = await crossmint.createWallet('user@example.com');
 *
 * // Sign message
 * const signature = await crossmint.signMessage('user@example.com', 'Hello');
 *
 * // Send transaction
 * const tx = await crossmint.sendTransaction('user@example.com', {
 *   to: '0x...',
 *   value: '1000000', // in wei
 * });
 * ```
 */
class CrossmintService {
  private client: unknown = null;
  private config: CrossmintConfig;
  private initialized = false;
  private walletCache = new Map<string, EmailWallet>();

  constructor(config: CrossmintConfig) {
    this.config = config;
    this.validateConfig();
  }

  /**
   * Validates configuration
   */
  private validateConfig(): void {
    if (!this.config.projectId) {
      console.warn(
        '[Crossmint] No project ID configured. Set VITE_CROSSMINT_PROJECT_ID in environment.'
      );
    }

    if (!['staging', 'production'].includes(this.config.environment)) {
      throw new CrossmintError(
        'Invalid environment. Must be "staging" or "production".',
        'INVALID_CONFIG',
        { environment: this.config.environment }
      );
    }
  }

  /**
   * Initializes the Crossmint SDK
   * Call this once when the application starts
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      console.log('[Crossmint] Already initialized');
      return;
    }

    if (!this.config.projectId) {
      throw new CrossmintError(
        'Cannot initialize: Missing VITE_CROSSMINT_PROJECT_ID',
        'INVALID_CONFIG'
      );
    }

    try {
      console.log(
        `[Crossmint] Initializing in ${this.config.environment} mode...`
      );

      // TODO: Import and initialize actual SDK when installed
      // import { CrossmintWallet } from '@crossmint/wallets-sdk';
      // this.client = new CrossmintWallet({
      //   projectId: this.config.projectId,
      //   environment: this.config.environment,
      // });

      // For now, create a mock client for development
      this.client = {
        projectId: this.config.projectId,
        environment: this.config.environment,
      };

      this.initialized = true;
      console.log('[Crossmint] Initialized successfully');
    } catch (error) {
      console.error('[Crossmint] Initialization failed:', error);
      throw new CrossmintError(
        'Failed to initialize Crossmint SDK',
        'NETWORK_ERROR',
        { originalError: String(error) }
      );
    }
  }

  /**
   * Ensures the service is initialized before operations
   */
  private ensureInitialized(): void {
    if (!this.initialized || !this.client) {
      throw new CrossmintError(
        'Crossmint not initialized. Call initialize() first.',
        'NOT_INITIALIZED'
      );
    }
  }

  /**
   * Creates a custodial wallet for an email address
   *
   * @param email - User's email address
   * @param chain - Blockchain to create wallet on (default: base)
   * @returns The created wallet information
   */
  async createWallet(
    email: string,
    chain: SupportedChain = DEFAULT_CHAIN
  ): Promise<EmailWallet> {
    this.ensureInitialized();

    if (!isValidEmail(email)) {
      throw new CrossmintError('Invalid email format', 'INVALID_EMAIL', {
        email,
      });
    }

    const cacheKey = `${email}:${chain}`;

    // Check cache first
    const cached = this.walletCache.get(cacheKey);
    if (cached) {
      console.log(`[Crossmint] Returning cached wallet for ${email}`);
      return cached;
    }

    try {
      console.log(`[Crossmint] Creating wallet for ${email} on ${chain}...`);

      // TODO: Implement actual SDK call when installed
      // const result = await this.client.createWallet({
      //   email,
      //   chain,
      // });

      // Mock implementation for development
      const wallet: EmailWallet = {
        address: generateMockAddress(email),
        email,
        chain,
        createdAt: new Date(),
      };

      // Cache the result
      this.walletCache.set(cacheKey, wallet);

      console.log(`[Crossmint] Wallet created: ${wallet.address}`);
      return wallet;
    } catch (error) {
      console.error('[Crossmint] Wallet creation failed:', error);
      throw new CrossmintError(
        'Failed to create wallet',
        'WALLET_CREATION_FAILED',
        { email, chain, originalError: String(error) }
      );
    }
  }

  /**
   * Gets an existing wallet for an email address
   *
   * @param email - User's email address
   * @param chain - Blockchain to look up (default: base)
   * @returns The wallet if found, null otherwise
   */
  async getWallet(
    email: string,
    chain: SupportedChain = DEFAULT_CHAIN
  ): Promise<EmailWallet | null> {
    this.ensureInitialized();

    if (!isValidEmail(email)) {
      throw new CrossmintError('Invalid email format', 'INVALID_EMAIL', {
        email,
      });
    }

    const cacheKey = `${email}:${chain}`;

    // Check cache first
    const cached = this.walletCache.get(cacheKey);
    if (cached) {
      return cached;
    }

    try {
      console.log(`[Crossmint] Looking up wallet for ${email}...`);

      // TODO: Implement actual SDK call when installed
      // const result = await this.client.getWallet({
      //   email,
      //   chain,
      // });
      // if (!result) return null;

      // For development, return null if not in cache
      return null;
    } catch (error) {
      console.error('[Crossmint] Wallet lookup failed:', error);
      return null;
    }
  }

  /**
   * Gets or creates a wallet for an email address
   * This is the recommended method for most use cases
   *
   * @param email - User's email address
   * @param chain - Blockchain (default: base)
   * @returns The wallet (existing or newly created)
   */
  async getOrCreateWallet(
    email: string,
    chain: SupportedChain = DEFAULT_CHAIN
  ): Promise<EmailWallet> {
    const existing = await this.getWallet(email, chain);
    if (existing) {
      return existing;
    }
    return this.createWallet(email, chain);
  }

  /**
   * Signs a message with the user's wallet
   *
   * @param email - User's email address
   * @param message - Message to sign
   * @returns The signature result
   */
  async signMessage(email: string, message: string): Promise<SignatureResult> {
    this.ensureInitialized();

    if (!isValidEmail(email)) {
      throw new CrossmintError('Invalid email format', 'INVALID_EMAIL', {
        email,
      });
    }

    if (!message || message.length === 0) {
      throw new CrossmintError(
        'Message cannot be empty',
        'SIGNATURE_FAILED',
        { email }
      );
    }

    try {
      console.log(`[Crossmint] Signing message for ${email}...`);

      // TODO: Implement actual SDK call when installed
      // const result = await this.client.signMessage({
      //   email,
      //   message,
      // });

      // Mock implementation for development
      const signature = `0x${Buffer.from(
        `mock_sig_${email}_${message.slice(0, 10)}`
      ).toString('hex')}`;

      return {
        signature,
        message,
      };
    } catch (error) {
      console.error('[Crossmint] Message signing failed:', error);
      throw new CrossmintError('Failed to sign message', 'SIGNATURE_FAILED', {
        email,
        originalError: String(error),
      });
    }
  }

  /**
   * Sends a transaction from the user's wallet
   *
   * @param email - User's email address
   * @param tx - Transaction request
   * @returns The transaction result
   */
  async sendTransaction(
    email: string,
    tx: TransactionRequest
  ): Promise<TransactionResult> {
    this.ensureInitialized();

    if (!isValidEmail(email)) {
      throw new CrossmintError('Invalid email format', 'INVALID_EMAIL', {
        email,
      });
    }

    if (!tx.to || !tx.to.startsWith('0x')) {
      throw new CrossmintError(
        'Invalid recipient address',
        'TRANSACTION_FAILED',
        { to: tx.to }
      );
    }

    const chainId = tx.chainId ?? CHAIN_IDS[DEFAULT_CHAIN];

    try {
      console.log(
        `[Crossmint] Sending transaction from ${email} to ${tx.to}...`
      );

      // TODO: Implement actual SDK call when installed
      // const result = await this.client.sendTransaction({
      //   email,
      //   to: tx.to,
      //   value: tx.value,
      //   data: tx.data,
      //   chainId,
      // });

      // Mock implementation for development
      const hash = `0x${Date.now().toString(16)}${Math.random().toString(16).slice(2, 10)}`;

      console.log(`[Crossmint] Transaction submitted: ${hash}`);

      return {
        hash,
        status: 'pending',
        chainId,
      };
    } catch (error) {
      console.error('[Crossmint] Transaction failed:', error);
      throw new CrossmintError(
        'Failed to send transaction',
        'TRANSACTION_FAILED',
        {
          email,
          tx,
          originalError: String(error),
        }
      );
    }
  }

  /**
   * Gets the current initialization status
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Gets the current configuration (without sensitive data)
   */
  getConfig(): { environment: string; hasProjectId: boolean } {
    return {
      environment: this.config.environment,
      hasProjectId: !!this.config.projectId,
    };
  }

  /**
   * Clears the wallet cache (useful for testing or logout)
   */
  clearCache(): void {
    this.walletCache.clear();
    console.log('[Crossmint] Cache cleared');
  }

  /**
   * Gets supported chains
   */
  getSupportedChains(): SupportedChain[] {
    return Object.keys(CHAIN_IDS) as SupportedChain[];
  }

  /**
   * Gets chain ID for a chain name
   */
  getChainId(chain: SupportedChain): number {
    return CHAIN_IDS[chain];
  }
}

/**
 * Generates a deterministic mock address for development
 * In production, this is replaced by actual Crossmint addresses
 */
function generateMockAddress(email: string): string {
  // Simple hash-like generation for consistent mock addresses
  let hash = 0;
  for (let i = 0; i < email.length; i++) {
    const char = email.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  const hexHash = Math.abs(hash).toString(16).padStart(8, '0');
  return `0x${hexHash}${'0'.repeat(32)}${hexHash}`;
}

/**
 * Singleton instance of CrossmintService
 *
 * Configuration is read from environment variables:
 * - VITE_CROSSMINT_PROJECT_ID: Your Crossmint project ID
 * - VITE_CROSSMINT_ENVIRONMENT: 'staging' or 'production' (auto-detected from VITE_MODE)
 */
export const crossmint = new CrossmintService({
  projectId: import.meta.env.VITE_CROSSMINT_PROJECT_ID || '',
  environment: import.meta.env.PROD ? 'production' : 'staging',
});

export default crossmint;
