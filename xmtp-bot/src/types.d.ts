declare module "irc-framework" {
  import { EventEmitter } from "events";

  interface ConnectionOptions {
    host: string;
    port: number;
    nick: string;
    tls?: boolean;
    sasl_mechanism?: string;
    account?: { account: string; password: string };
    auto_reconnect?: boolean;
    auto_reconnect_wait?: number;
    auto_reconnect_max_retries?: number;
  }

  class Client extends EventEmitter {
    constructor(options?: Partial<ConnectionOptions>);
    connected: boolean;
    connect(options?: Partial<ConnectionOptions>): void;
    quit(message?: string): void;
    join(channel: string): void;
    part(channel: string, message?: string): void;
    say(target: string, message: string): void;
    match(pattern: string, cb: (...args: any[]) => void): void;
    on(event: string, listener: (...args: any[]) => void): this;
  }

  export { Client };
}
