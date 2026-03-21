import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { getWorkerStore } from "../services/worker-store.js";
import { logger } from "../utils/logger.js";

export async function handleRegister(
  ctx: MessageContext<string>,
  _args: string[]
): Promise<void> {
  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) {
    await ctx.sendTextReply("No se pudo resolver tu direccion.");
    return;
  }

  const store = getWorkerStore();
  const worker = store.getByAddress(senderAddress);

  if (worker?.executorId) {
    await ctx.sendMarkdownReply(
      `Ya estas registrado como **${worker.name}**.\n` +
        `Executor ID: \`${worker.executorId}\``
    );
    return;
  }

  // Start registration flow
  store.setRegistrationProgress(senderAddress, { step: "name" });
  await ctx.sendTextReply(
    "Registro de Executor\n\n" +
      "Paso 1/2: Cual es tu nombre o alias?"
  );
}

export async function handleRegistrationText(
  ctx: MessageContext<string>,
  senderAddress: string,
  text: string
): Promise<void> {
  const store = getWorkerStore();
  const progress = store.getRegistrationProgress(senderAddress);

  if (!progress) {
    store.resetConversation(senderAddress);
    return;
  }

  switch (progress.step) {
    case "name": {
      const name = text.trim();
      if (name.length < 2 || name.length > 50) {
        await ctx.sendTextReply(
          "El nombre debe tener entre 2 y 50 caracteres. Intenta de nuevo:"
        );
        return;
      }
      store.setRegistrationProgress(senderAddress, { step: "email", name });
      await ctx.sendTextReply(
        `Nombre: ${name}\n\n` +
          `Paso 2/2: Tu email (opcional, escribe "skip" para omitir):`
      );
      break;
    }

    case "email": {
      const email = text.trim().toLowerCase();
      const name = progress.name!;
      const finalEmail =
        email === "skip" || email === "omitir" ? undefined : email;

      if (finalEmail && !finalEmail.includes("@")) {
        await ctx.sendTextReply(
          'Email invalido. Intenta de nuevo o escribe "skip":'
        );
        return;
      }

      // Confirm
      store.setRegistrationProgress(senderAddress, {
        step: "confirm",
        name,
        email: finalEmail,
      });
      await ctx.sendMarkdownReply(
        `**Confirmar registro:**\n\n` +
          `| Campo | Valor |\n` +
          `|-------|-------|\n` +
          `| Nombre | ${name} |\n` +
          `| Email | ${finalEmail ?? "\u2014"} |\n` +
          `| Wallet | \`${senderAddress.slice(0, 6)}...${senderAddress.slice(-4)}\` |\n\n` +
          `Escribe **si** para confirmar o **no** para cancelar.`
      );
      break;
    }

    case "confirm": {
      const answer = text.trim().toLowerCase();
      if (answer === "si" || answer === "yes" || answer === "s") {
        try {
          const result = await apiClient.post<any>(
            "/api/v1/workers/register",
            {
              wallet_address: senderAddress,
              name: progress.name,
              email: progress.email,
            }
          );

          const executorId = result.executor_id ?? result.id;
          store.register(senderAddress, executorId, progress.name!);

          await ctx.sendMarkdownReply(
            `**Registro exitoso!**\n\n` +
              `Bienvenido, **${progress.name}**.\n` +
              `Executor ID: \`${executorId}\`\n\n` +
              `Ahora puedes:\n` +
              `- \`/tasks\` \u2014 Ver tareas disponibles\n` +
              `- \`/apply <id>\` \u2014 Aplicar a una tarea\n` +
              `- \`/mytasks\` \u2014 Ver tus tareas activas`
          );
        } catch (err: any) {
          const msg =
            err?.response?.data?.detail ?? "Error al registrar.";
          logger.error(
            { err, sender: senderAddress },
            "Registration failed"
          );
          await ctx.sendTextReply(
            `Error: ${msg}\nIntenta de nuevo con /register`
          );
          store.resetConversation(senderAddress);
        }
      } else {
        await ctx.sendTextReply(
          "Registro cancelado. Usa /register para intentar de nuevo."
        );
        store.resetConversation(senderAddress);
      }
      break;
    }
  }
}
