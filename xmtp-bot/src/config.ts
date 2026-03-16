import "dotenv/config";

export const config = {
  xmtp: {
    env: (process.env.XMTP_ENV ?? "dev") as "local" | "dev" | "production",
    dbPath: process.env.XMTP_DB_PATH ?? "./data/xmtp",
  },
  em: {
    apiUrl: process.env.EM_API_URL ?? "https://api.execution.market",
    apiKey: process.env.EM_API_KEY ?? "",
    wsUrl: process.env.EM_WS_URL ?? "wss://api.execution.market/ws",
  },
  health: {
    port: parseInt(process.env.HEALTH_PORT ?? "8090", 10),
  },
  log: {
    level: process.env.LOG_LEVEL ?? "info",
  },
} as const;
