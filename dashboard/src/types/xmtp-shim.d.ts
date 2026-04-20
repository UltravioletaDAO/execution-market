// Type stub for @xmtp/browser-sdk — native module only available on Linux.
// The actual SDK is installed in Docker builds (Linux amd64).
// This shim prevents TypeScript errors on Windows/macOS dev machines.
declare module "@xmtp/browser-sdk" {
  /** XMTP v5+ identifier kinds */
  export enum IdentifierKind {
    Ethereum = "Ethereum",
    Passkey = "Passkey",
  }

  export interface Identifier {
    identifier: string;
    identifierKind: IdentifierKind;
  }

  /** XMTP v5+ signer interface accepted by Client.create() */
  export interface XMTPSigner {
    type: "EOA" | "SCW";
    getIdentifier(): Identifier | Promise<Identifier>;
    /** Must return the signature as a Uint8Array (raw bytes, not hex string) */
    signMessage(message: string): Promise<Uint8Array>;
    /** Required when type === "SCW" */
    getChainId?(): bigint;
    getBlockNumber?(): bigint | undefined;
  }
  /** Alias used by the XMTP docs */
  export type Signer = XMTPSigner;

  /** A single decoded XMTP message from the network (v5 — MLS) */
  export interface DecodedMessage {
    id: string;
    content: string | unknown;
    senderInboxId: string;
    sentAt: Date;
    sentAtNs?: bigint;
    conversationId?: string;
  }

  export interface MessageListOptions {
    limit?: number;
    /** Cursor: fetch messages sent before this timestamp (ns or Date) */
    before?: Date | bigint;
    /** Cursor: fetch messages sent after this timestamp (ns or Date) */
    after?: Date | bigint;
  }

  /** An XMTP conversation (v5 — MLS group, also used for DMs). */
  export interface Conversation {
    id: string;
    /** Only present on DMs. Returns the peer's inbox ID (async). */
    peerInboxId?(): Promise<string>;
    messages(opts?: MessageListOptions): Promise<DecodedMessage[]>;
    send(content: string): Promise<string>;
    streamMessages(): AsyncIterable<DecodedMessage>;
    lastMessage?: DecodedMessage | undefined;
  }

  export interface InboxState {
    inboxId: string;
    identifiers: Identifier[];
    recoveryIdentifier?: Identifier;
  }

  export class Client {
    inboxId: string;
    static create(signer: XMTPSigner, options?: { env?: "production" | "dev" | "local" }): Promise<Client>;
    conversations: {
      list(opts?: { consentStates?: unknown[]; limit?: number }): Promise<Conversation[]>;
      /** v5: open/create a DM by identifier (e.g. Ethereum address). */
      newDmWithIdentifier(identifier: Identifier): Promise<Conversation>;
      /** v5: open/create a DM by peer inbox id. */
      newDm(peerInboxId: string): Promise<Conversation>;
      /** Stream newly created conversations. */
      stream(): Promise<AsyncIterable<Conversation>>;
    };
    /** Resolve address(es) to inbox id(s). */
    findInboxIdByIdentifier(identifier: Identifier): Promise<string | undefined>;
    inboxStateFromInboxIds(inboxIds: string[], refresh?: boolean): Promise<InboxState[]>;
    close(): Promise<void>;
  }

}
