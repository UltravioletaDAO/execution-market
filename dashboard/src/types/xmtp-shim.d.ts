// Type stub for @xmtp/browser-sdk — native module only available on Linux.
// The actual SDK is installed in Docker builds (Linux amd64).
// This shim prevents TypeScript errors on Windows/macOS dev machines.
declare module "@xmtp/browser-sdk" {
  /** Minimal signer interface accepted by XMTP Client.create() */
  export interface XMTPSigner {
    getAddress(): string | Promise<string>;
    /** signMessage must return a resolved string (never undefined) */
    signMessage(message: string): Promise<string>;
  }

  /** A single decoded XMTP message from the network */
  export interface DecodedMessage {
    id: string;
    content: string | unknown;
    senderAddress: string;
    sentAt: Date;
    conversationId?: string;
  }

  export interface MessageListOptions {
    limit?: number;
    /** Cursor: fetch messages sent before this date */
    before?: Date;
    /** Cursor: fetch messages sent after this date */
    after?: Date;
  }

  /** An XMTP conversation (DM channel) */
  export interface Conversation {
    id?: string;
    topic: string;
    peerAddress: string;
    messages(opts?: MessageListOptions): Promise<DecodedMessage[]>;
    send(content: string): Promise<void>;
    streamMessages(): AsyncIterable<DecodedMessage>;
  }

  export class Client {
    static create(signer: XMTPSigner, options?: { env?: "production" | "dev" | "local" }): Promise<Client>;
    conversations: {
      list(): Promise<Conversation[]>;
      newConversation(peerAddress: string): Promise<Conversation>;
      /** Stream newly created conversations as they arrive */
      stream(): AsyncIterable<Conversation>;
    };
    close(): Promise<void>;
  }

  export function createSigner(wallet: {
    signMessage(message: string): Promise<string>;
    account?: { address?: string };
  }): XMTPSigner;
}
