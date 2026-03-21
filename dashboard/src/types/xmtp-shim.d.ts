// Type stub for @xmtp/browser-sdk — native module only available on Linux.
// The actual SDK is installed in Docker builds (Linux amd64).
// This shim prevents TypeScript errors on Windows/macOS dev machines.
declare module "@xmtp/browser-sdk" {
  export class Client {
    static create(signer: any, options?: any): Promise<Client>;
    conversations: {
      list(): Promise<any[]>;
      newConversation(peerAddress: string): Promise<any>;
    };
    close(): Promise<void>;
  }
  export function createSigner(wallet: any): any;
}
