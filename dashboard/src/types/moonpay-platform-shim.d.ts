// Type stub for @moonpay/platform — Phase 1D spike.
// The dep isn't in package.json yet (the spike imports it dynamically and
// shows an install hint if missing). This shim keeps `tsc` happy on dev
// machines that haven't run `npm install @moonpay/platform`.
declare module "@moonpay/platform" {
  export interface MoonPayClientConfig {
    sessionToken: string;
  }

  export interface FrameMountConfig {
    target: HTMLElement;
    baseCurrencyCode?: string;
    baseCurrencyAmount?: number;
    currencyCode?: string;
    walletAddress?: string;
    [key: string]: unknown;
  }

  export interface MoonPayClient {
    connect(): Promise<void>;
    setupApplePay?(cfg: FrameMountConfig): Promise<unknown>;
    mount?(target: HTMLElement, cfg: Record<string, unknown>): Promise<unknown>;
    on?(event: string, cb: (payload: unknown) => void): void;
    destroy?(): Promise<void>;
  }

  export function createClient(cfg: MoonPayClientConfig): Promise<MoonPayClient> | MoonPayClient;
}
