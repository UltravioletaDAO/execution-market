import type { MessageContext } from "@xmtp/agent-sdk";
import { startSubmission } from "../submission/flow.js";

export async function handleSubmit(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  if (args.length === 0) {
    await ctx.sendTextReply(
      "Uso: /submit <task_id>\nEjemplo: /submit abc12345"
    );
    return;
  }
  await startSubmission(ctx, args[0]);
}
