import { Agent, CommandRouter, type MessageContext } from "@xmtp/agent-sdk";
import { getWorkerStore } from "../services/worker-store.js";
import { logger } from "../utils/logger.js";
import { handleRegister, handleRegistrationText } from "./register.js";
import { handleHelp } from "./help.js";
import { handleTasks } from "./tasks.js";
import { handleApply } from "./apply.js";
import { handleStatus } from "./status.js";
import { handleMyTasks } from "./mytasks.js";

// ─── Command handler type ─────────────────────────────────────────
export type CommandHandler = (
  ctx: MessageContext<string>,
  args: string[]
) => Promise<void>;

// ─── Command definition ───────────────────────────────────────────
export interface CommandDefinition {
  name: string;
  usage: string;
  description: string;
  handler: CommandHandler;
}

// ─── Command registry ─────────────────────────────────────────────
const commands: CommandDefinition[] = [
  {
    name: "help",
    usage: "/help",
    description: "Muestra este menu de ayuda",
    handler: handleHelp,
  },
  {
    name: "tasks",
    usage: "/tasks [categoria]",
    description: "Lista tareas disponibles",
    handler: handleTasks,
  },
  {
    name: "apply",
    usage: "/apply <task_id>",
    description: "Aplicar a una tarea",
    handler: handleApply,
  },
  {
    name: "status",
    usage: "/status <task_id>",
    description: "Ver estado de una tarea",
    handler: handleStatus,
  },
  {
    name: "mytasks",
    usage: "/mytasks",
    description: "Ver tus tareas activas",
    handler: handleMyTasks,
  },
  {
    name: "register",
    usage: "/register",
    description: "Registrarte como executor",
    handler: handleRegister,
  },
];

export function getCommandList(): CommandDefinition[] {
  return commands;
}

export function findCommand(name: string): CommandDefinition | undefined {
  return commands.find((c) => c.name === name.toLowerCase());
}

// ─── Register handlers on the XMTP Agent ──────────────────────────
export function registerHandlers(agent: Agent): void {
  const router = new CommandRouter({ helpCommand: "/help" });

  // Register each command with the SDK router
  for (const cmd of commands) {
    router.command(`/${cmd.name}`, cmd.description, async (ctx) => {
      const text = (ctx.message.content as string) ?? "";
      const parts = text.trim().split(/\s+/);
      const args = parts.slice(1);
      await cmd.handler(ctx as MessageContext<string>, args);
    });
  }

  // Default handler for non-command text
  router.default(async (ctx) => {
    const senderAddress = await ctx.getSenderAddress();
    if (!senderAddress) {
      logger.warn("Could not resolve sender address");
      return;
    }

    const text = (ctx.message.content as string) ?? "";
    const store = getWorkerStore();
    const state = store.getConversationState(senderAddress);

    // Route to registration flow if active
    if (state === "registration") {
      await handleRegistrationText(ctx as MessageContext<string>, senderAddress, text);
      return;
    }

    // Welcome / fallback for unknown text
    await ctx.sendMarkdownReply(
      "Hola! Soy el bot de **Execution Market**.\n\n" +
        "Escribe `/help` para ver los comandos disponibles."
    );
  });

  // Apply the router as middleware on the agent
  agent.use(router.middleware());

  logger.info(
    { commands: commands.map((c) => c.name) },
    "Command handlers registered"
  );
}

// Re-exports
export { handleHelp } from "./help.js";
export { handleTasks } from "./tasks.js";
export { handleApply } from "./apply.js";
export { handleStatus } from "./status.js";
export { handleMyTasks } from "./mytasks.js";
export { handleRegister, handleRegistrationText } from "./register.js";
