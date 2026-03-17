declare module "irc-framework" {
  export class Client {
    connected: boolean;
    connect(options: {
      host: string;
      port: number;
      nick: string;
      tls?: boolean;
      account?: { account: string; password: string };
    }): void;
    on(event: string, handler: (...args: any[]) => void): void;
    join(channel: string): void;
    say(target: string, message: string): void;
    quit(message?: string): void;
  }
}
