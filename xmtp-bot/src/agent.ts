import { Agent } from "@xmtp/agent-sdk";
import { config } from "./config.js";
import { logger } from "./utils/logger.js";

let agent: Agent | undefined;

/**
 * Creates and initializes the XMTP Agent from environment variables.
 * Expects XMTP_KEY (hex private key) in the environment.
 */
export async function createAgent(): Promise<Agent> {
  logger.info(
    { env: config.xmtp.env, dbPath: config.xmtp.dbPath },
    "Initializing XMTP agent"
  );

  agent = await Agent.createFromEnv({
    env: config.xmtp.env,
    dbPath: config.xmtp.dbPath,
  });

  logger.info(
    { address: agent.address },
    "XMTP agent initialized"
  );

  return agent;
}

/**
 * Returns the current agent instance. Throws if not yet created.
 */
export function getAgent(): Agent {
  if (!agent) {
    throw new Error("XMTP agent not initialized — call createAgent() first");
  }
  return agent;
}
