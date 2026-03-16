import express from "express";
import { config } from "./config.js";
import { logger } from "./utils/logger.js";
import { createAgent } from "./agent.js";
import { registerHandlers } from "./commands/index.js";

async function main(): Promise<void> {
  // ─── Health-check server ──────────────────────────────────────
  const app = express();
  const startedAt = new Date().toISOString();

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", startedAt, uptime: process.uptime() });
  });

  const server = app.listen(config.health.port, () => {
    logger.info({ port: config.health.port }, "Health-check server listening");
  });

  // ─── XMTP Agent ──────────────────────────────────────────────
  const agent = await createAgent();

  // Register command handlers (uses CommandRouter middleware)
  registerHandlers(agent);

  // Error handling
  agent.on("unhandledError", (error) => {
    logger.error({ err: error }, "Unhandled agent error");
  });

  // ─── Connect notification dispatcher to XMTP agent ──────────
  try {
    const { setSendMessageFn } = await import("./services/notification-dispatcher.js");
    setSendMessageFn(async (peerAddress: string, text: string) => {
      const dm = await agent.createDmWithAddress(peerAddress as `0x${string}`);
      await dm.sendText(text);
    });
    logger.info("Notification dispatcher connected to XMTP agent");
  } catch (err) {
    logger.warn({ err }, "Failed to connect notification dispatcher");
  }

  // ─── WebSocket listener ────────────────────────────────────
  try {
    const { startWsListener } = await import("./services/ws-listener.js");
    startWsListener();
    logger.info("WebSocket listener started");
  } catch {
    logger.warn("ws-listener not available — skipping");
  }

  // ─── Graceful shutdown ────────────────────────────────────────
  const shutdown = async (signal: string) => {
    logger.info({ signal }, "Shutting down...");
    try {
      await agent.stop();
    } catch (err) {
      logger.error({ err }, "Error stopping agent");
    }
    server.close(() => {
      logger.info("Health server closed");
      process.exit(0);
    });
    // Force exit after 10s if graceful close hangs
    setTimeout(() => process.exit(1), 10_000).unref();
  };

  process.on("SIGTERM", () => shutdown("SIGTERM"));
  process.on("SIGINT", () => shutdown("SIGINT"));

  // ─── Start agent (blocking — streams messages) ───────────────
  logger.info({ address: agent.address }, "Starting XMTP agent...");
  await agent.start();
}

main().catch((err) => {
  logger.fatal({ err }, "Fatal error — exiting");
  process.exit(1);
});
