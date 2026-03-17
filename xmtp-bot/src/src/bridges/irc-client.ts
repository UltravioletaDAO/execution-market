import { Client } from "irc-framework";
import { config } from "../config.js";
import { logger } from "../utils/logger.js";

type MessageHandler = (channel: string, nick: string, text: string) => void;

interface IrcHealth {
  connected: boolean;
  reconnects: number;
  messagesIn: number;
  messagesOut: number;
  lastMessageAt: string | null;
}

let client: Client | null = null;
let messageHandler: MessageHandler | null = null;
let reconnects = 0;
let messagesIn = 0;
let messagesOut = 0;
let lastMessageAt: Date | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;
const MAX_RECONNECT_DELAY = 30_000;

export function onIrcMessage(handler: MessageHandler): void {
  messageHandler = handler;
}

export function getIrcHealth(): IrcHealth {
  return {
    connected: client?.connected ?? false,
    reconnects,
    messagesIn,
    messagesOut,
    lastMessageAt: lastMessageAt?.toISOString() ?? null,
  };
}

export function startIrcClient(): void {
  if (!config.irc.enabled) {
    logger.info("IRC bridge disabled (IRC_ENABLED != true)");
    return;
  }
  connect();
}

function connect(): void {
  client = new Client();

  const connectOpts: Parameters<typeof client.connect>[0] = {
    host: config.irc.host,
    port: config.irc.port,
    nick: config.irc.nick,
    tls: config.irc.tls,
  };

  // SASL PLAIN authentication (MeshRelay P0)
  if (config.irc.saslUser && config.irc.saslPass) {
    connectOpts.account = {
      account: config.irc.saslUser,
      password: config.irc.saslPass,
    };
    logger.info("IRC connecting with SASL PLAIN auth");
  }

  client.connect(connectOpts);

  client.on("registered", () => {
    logger.info(
      { nick: config.irc.nick, host: config.irc.host },
      "IRC connected",
    );
    reconnectDelay = 1000;

    for (const channel of config.irc.channels) {
      client!.join(channel);
      logger.info({ channel }, "Joined IRC channel");
    }
  });

  client.on("message", (event: any) => {
    if (event.nick === config.irc.nick) return; // Ignore own messages
    messagesIn++;
    lastMessageAt = new Date();
    logger.debug(
      { channel: event.target, nick: event.nick },
      "IRC message received",
    );

    if (messageHandler) {
      messageHandler(event.target, event.nick, event.message);
    }
  });

  client.on("close", () => {
    logger.warn(
      { delay: reconnectDelay },
      "IRC connection closed, reconnecting...",
    );
    reconnects++;
    scheduleReconnect();
  });

  client.on("socket close", () => {
    if (client?.connected) return;
    logger.warn("IRC socket closed");
    scheduleReconnect();
  });
}

function scheduleReconnect(): void {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
}

export function sendToChannel(channel: string, text: string): void {
  if (!client?.connected) {
    logger.warn({ channel }, "IRC not connected, cannot send message");
    return;
  }
  // IRC messages max ~512 bytes. Split long messages.
  const lines = text.split("\n");
  for (const line of lines) {
    if (line.trim()) {
      client.say(channel, line.slice(0, 450));
      messagesOut++;
    }
  }
  lastMessageAt = new Date();
}

export function stopIrcClient(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (client) {
    client.quit("Shutting down");
    client = null;
  }
  logger.info("IRC client stopped");
}
