import { Agent, CommandRouter, type MessageContext } from "@xmtp/agent-sdk";
import { getWorkerStore } from "../services/worker-store.js";
import { logger } from "../utils/logger.js";
import { handleRegister, handleRegistrationText } from "./register.js";
import { handleHelp } from "./help.js";
import { handleTasks } from "./tasks.js";
import { handleApply } from "./apply.js";
import { handleStatus } from "./status.js";
import { handleMyTasks } from "./mytasks.js";
import { handleSubmit } from "./submit.js";
import { handleBalance } from "./balance.js";
import { handleEarnings } from "./earnings.js";
import { handleRate } from "./rate.js";
import { handleReputation } from "./reputation.js";
import {
  handleSubmissionText,
  handleSubmissionSkip,
  handleSubmissionCancel,
  handleSubmissionDone,
  getActiveDraft,
  isSubmissionTimedOut,
  clearDraft,
} from "../submission/flow.js";

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
    name: "submit",
    usage: "/submit <task_id>",
    description: "Enviar evidencia de tarea",
    handler: handleSubmit,
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
    name: "balance",
    usage: "/balance",
    description: "Ver balance USDC en todas las chains",
    handler: handleBalance,
  },
  {
    name: "earnings",
    usage: "/earnings",
    description: "Ver ganancias totales",
    handler: handleEarnings,
  },
  {
    name: "rate",
    usage: "/rate <task_id> <1-5> [comentario]",
    description: "Calificar agente/worker",
    handler: handleRate,
  },
  {
    name: "reputation",
    usage: "/reputation [address]",
    description: "Ver reputacion on-chain",
    handler: handleReputation,
  },
  {
    name: "register",
    usage: "/register",
    description: "Registrarte como executor",
    handler: handleRegister,
  },
  {
    name: "skip",
    usage: "/skip",
    description: "Omitir pieza opcional (durante submission)",
    handler: async (ctx, _args) => {
      const senderAddress = await ctx.getSenderAddress();
      if (!senderAddress) return;
      await handleSubmissionSkip(ctx, senderAddress);
    },
  },
  {
    name: "cancel",
    usage: "/cancel",
    description: "Cancelar submission activa",
    handler: async (ctx, _args) => {
      const senderAddress = await ctx.getSenderAddress();
      if (!senderAddress) return;
      await handleSubmissionCancel(ctx, senderAddress);
    },
  },
  {
    name: "done",
    usage: "/done",
    description: "Enviar submission con las piezas recolectadas",
    handler: async (ctx, _args) => {
      const senderAddress = await ctx.getSenderAddress();
      if (!senderAddress) return;
      await handleSubmissionDone(ctx, senderAddress);
    },
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

    // Route to submission flow if active
    if (state === "submission") {
      const draft = getActiveDraft(senderAddress);
      if (draft && isSubmissionTimedOut(draft)) {
        clearDraft(senderAddress);
        store.resetConversation(senderAddress);
        await ctx.sendTextReply(
          "Submission expirada (30 min). Usa /submit para reiniciar."
        );
        return;
      }
      await handleSubmissionText(
        ctx as MessageContext<string>,
        senderAddress,
        text
      );
      return;
    }

    // Route to registration flow if active
    if (state === "registration") {
      await handleRegistrationText(
        ctx as MessageContext<string>,
        senderAddress,
        text
      );
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
export { handleSubmit } from "./submit.js";
export { handleBalance } from "./balance.js";
export { handleEarnings } from "./earnings.js";
export { handleRate } from "./rate.js";
export { handleReputation } from "./reputation.js";
