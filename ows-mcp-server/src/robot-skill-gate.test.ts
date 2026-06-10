/**
 * Runtime smoke test for the em-robot-skill gate (OWS_ROBOT_SKILL_ENABLED).
 *
 * Run: npx tsx --test src/robot-skill-gate.test.ts
 *
 * Spawns the real server over stdio and counts tools via MCP `tools/list`:
 *   - gate unset (default)        → 11 core tools, no robot_* tools
 *   - OWS_ROBOT_SKILL_ENABLED=true → 16 tools (11 core + 5 robot_*)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER_PATH = path.join(__dirname, "server.ts");

const CORE_TOOL_COUNT = 11;
const ROBOT_TOOL_COUNT = 5;

/** Boot the server with the given env, run initialize + tools/list, return tool names. */
async function listTools(extraEnv: Record<string, string | undefined>): Promise<string[]> {
  const env = { ...process.env, ...extraEnv };
  delete env.OWS_ROBOT_SKILL_ENABLED;
  for (const [k, v] of Object.entries(extraEnv)) {
    if (v !== undefined) env[k] = v;
  }

  const child = spawn(process.execPath, ["--import", "tsx", SERVER_PATH], {
    env,
    stdio: ["pipe", "pipe", "pipe"],
  });

  const messages = [
    {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "robot-skill-gate-test", version: "0.0.0" },
      },
    },
    { jsonrpc: "2.0", method: "notifications/initialized" },
    { jsonrpc: "2.0", id: 2, method: "tools/list" },
  ];

  try {
    return await new Promise<string[]>((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error("timed out waiting for tools/list response")),
        90_000
      );
      let buffer = "";
      child.stdout.on("data", (chunk: Buffer) => {
        buffer += chunk.toString("utf-8");
        let nl: number;
        while ((nl = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, nl).trim();
          buffer = buffer.slice(nl + 1);
          if (!line) continue;
          let msg: { id?: number; result?: { tools?: Array<{ name: string }> } };
          try {
            msg = JSON.parse(line);
          } catch {
            continue;
          }
          if (msg.id === 2 && msg.result?.tools) {
            clearTimeout(timer);
            resolve(msg.result.tools.map((t) => t.name));
          }
        }
      });
      child.on("error", (err) => {
        clearTimeout(timer);
        reject(err);
      });
      child.on("exit", (code) => {
        clearTimeout(timer);
        reject(new Error(`server exited early (code ${code})`));
      });
      child.stdin.write(messages.map((m) => JSON.stringify(m)).join("\n") + "\n");
    });
  } finally {
    child.kill();
  }
}

test("gate OFF (default): only the core tools are registered", async () => {
  const tools = await listTools({});
  const robotTools = tools.filter((t) => t.startsWith("robot_"));
  assert.equal(robotTools.length, 0, `robot_* tools must NOT register: ${robotTools}`);
  assert.equal(tools.length, CORE_TOOL_COUNT, `expected ${CORE_TOOL_COUNT} core tools, got: ${tools}`);
});

test("gate ON (OWS_ROBOT_SKILL_ENABLED=true): core + 5 robot tools", async () => {
  const tools = await listTools({ OWS_ROBOT_SKILL_ENABLED: "true" });
  const robotTools = tools.filter((t) => t.startsWith("robot_"));
  assert.equal(robotTools.length, ROBOT_TOOL_COUNT, `expected ${ROBOT_TOOL_COUNT} robot tools, got: ${robotTools}`);
  assert.equal(tools.length, CORE_TOOL_COUNT + ROBOT_TOOL_COUNT);
});
