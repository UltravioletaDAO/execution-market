import type { MessageContext } from "@xmtp/agent-sdk";
import { getCommandList } from "./index.js";

export async function handleHelp(
  ctx: MessageContext<string>,
  _args: string[]
): Promise<void> {
  const cmds = getCommandList();
  const lines = [
    "**Execution Market Bot**",
    "",
    "Comandos disponibles:",
    ...cmds.map((c) => `- \`${c.usage}\` — ${c.description}`),
    "",
    "Envia un comando para empezar.",
  ];
  await ctx.sendMarkdownReply(lines.join("\n"));
}
