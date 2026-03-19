import "dotenv/config";

export const config = {
  xmtp: {
    env: (process.env.XMTP_ENV ?? "dev") as "local" | "dev" | "production",
    dbPath: process.env.XMTP_DB_PATH ?? "./data/xmtp/bot.db3",
  },
  em: {
    apiUrl: process.env.EM_API_URL ?? "https://api.execution.market",
    apiKey: process.env.EM_API_KEY ?? "",
    wsUrl: process.env.EM_WS_URL ?? "wss://api.execution.market/ws",
  },
  health: {
    port: parseInt(process.env.HEALTH_PORT ?? "8090", 10),
  },
  irc: {
    enabled: process.env.IRC_ENABLED === "true",
    host: process.env.IRC_HOST ?? "irc.meshrelay.xyz",
    port: parseInt(process.env.IRC_PORT ?? "6697", 10),
    tls: process.env.IRC_TLS !== "false",
    nick: process.env.IRC_NICK ?? "em-bot",
    saslUser: process.env.IRC_SASL_USER ?? "",
    saslPass: process.env.IRC_SASL_PASS ?? "",
    channels: (process.env.IRC_CHANNELS ?? "#bounties,#Agents")
      .split(",")
      .map((c) => c.trim()),
  },
  supabase: {
    url: process.env.SUPABASE_URL ?? "",
    serviceKey: process.env.SUPABASE_SERVICE_KEY ?? "",
  },
  log: {
    level: process.env.LOG_LEVEL ?? "info",
  },
} as const;
