import WebSocket from "ws";
import { config } from "../config.js";
import { logger } from "../utils/logger.js";
import {
  notifyTaskCreated,
  notifyTaskAssigned,
  notifySubmissionApproved,
  notifySubmissionRejected,
  notifyNewRating,
} from "./notification-dispatcher.js";
import { handlePaymentEvent } from "./payment-monitor.js";
import { createTaskGroup, getTaskGroup } from "./group-manager.js";
import {
  onTaskStatusChanged,
  onEvidenceSubmitted,
  onSubmissionApproved,
  onSubmissionRejected,
  onRatingReceived,
} from "./group-lifecycle.js";

// Optional IRC bridge — may not be available
let ircBridge: {
  broadcastTaskToIrc: (task: any) => void;
  broadcastStatusToIrc: (taskId: string, status: string, extra?: string) => void;
  broadcastPaymentToIrc: (task: any, txHash: string) => void;
} | null = null;

import("../bridges/meshrelay.js")
  .then((mod) => {
    ircBridge = {
      broadcastTaskToIrc: mod.broadcastTaskToIrc,
      broadcastStatusToIrc: mod.broadcastStatusToIrc,
      broadcastPaymentToIrc: mod.broadcastPaymentToIrc,
    };
  })
  .catch(() => { /* bridge not available */ });

let ws: WebSocket | null = null;
let reconnectDelay = 1000;
const MAX_RECONNECT_DELAY = 30_000;

export function startWsListener(): void {
  if (!config.em.wsUrl) {
    logger.warn("EM_WS_URL not set, skipping WebSocket listener");
    return;
  }
  connect();
}

function connect(): void {
  const url = config.em.apiKey
    ? `${config.em.wsUrl}?api_key=${config.em.apiKey}`
    : config.em.wsUrl;

  logger.info({ url: config.em.wsUrl }, "Connecting to EM WebSocket...");
  ws = new WebSocket(url);

  ws.on("open", () => {
    logger.info("WebSocket connected to EM API");
    reconnectDelay = 1000;

    // Subscribe to global events
    ws!.send(JSON.stringify({ type: "subscribe", payload: { room: "global" } }));
  });

  ws.on("message", async (data) => {
    try {
      const event = JSON.parse(data.toString());

      if (event.type === "heartbeat" || event.type === "pong") return;
      if (event.event === "heartbeat" || event.event === "pong") return;

      // Normalize server WebSocket event format to bot format
      // Server sends: {event: "WorkerAssigned", payload: {...}}
      // Bot expects: {type: "task.assigned", data: {...}}
      const normalized = normalizeEvent(event);
      if (!normalized) return;

      logger.debug({ eventType: normalized.type }, "WS event received");
      await handleEvent(normalized);
    } catch (err) {
      logger.error({ err }, "WS message parse error");
    }
  });

  ws.on("close", (code) => {
    logger.warn({ code, delay: reconnectDelay }, "WebSocket closed, reconnecting...");
    setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
  });

  ws.on("error", (err) => {
    logger.error({ err: err.message }, "WebSocket error");
  });
}

/** Maps MCP server event names to bot event types */
const EVENT_TYPE_MAP: Record<string, string> = {
  "WorkerAssigned": "task.assigned",
  "SubmissionApproved": "submission.approved",
  "SubmissionRejected": "submission.rejected",
  "TaskCreated": "task.created",
  "TaskCancelled": "task.cancelled",
  "TaskUpdated": "task.status_changed",
  "PaymentReleased": "payment.released",
  "SubmissionReceived": "submission.received",
};

/**
 * Normalize incoming WS events to the bot's expected format.
 * Server sends: {event: "WorkerAssigned", payload: {...}, room: "...", metadata: {...}}
 * Bot expects: {type: "task.assigned", data: {...}}
 * If the event already has a `type` field (old format), pass through as-is.
 */
function normalizeEvent(event: any): any | null {
  // Old format already has `type` — pass through
  if (event.type) return event;

  // New server format uses `event` field
  if (event.event) {
    const mappedType = EVENT_TYPE_MAP[event.event];
    if (!mappedType) {
      logger.debug({ serverEvent: event.event }, "Unknown server event, skipping");
      return null;
    }
    return { type: mappedType, data: event.payload };
  }

  return null;
}

async function handleEvent(event: any): Promise<void> {
  const data = event.data ?? event.payload;
  if (!data) return;

  switch (event.type) {
    case "task.created":
      await notifyTaskCreated(data);
      ircBridge?.broadcastTaskToIrc(data);
      break;

    case "task.assigned": {
      const workerAddress = data.executor_wallet ?? data.worker_wallet ?? data.worker_address;
      if (workerAddress) {
        await notifyTaskAssigned(workerAddress, data);
      }
      // Create XMTP group for this task
      await createTaskGroup({
        taskId: data.id ?? data.task_id,
        taskTitle: data.title ?? data.task_title ?? "Task",
        bounty: data.bounty_usdc ?? data.bounty ?? "0",
        chain: data.payment_network ?? data.chain ?? "base",
        workerAddress,
        agentAddress: data.agent_wallet ?? data.publisher_wallet,
      });
      ircBridge?.broadcastStatusToIrc(data.id ?? data.task_id, "accepted", data.title);
      break;
    }

    case "submission.approved": {
      const addr = data.executor_wallet ?? data.worker_wallet ?? data.worker_address;
      if (addr) {
        await notifySubmissionApproved(addr, data, data.tx_hash);
      }
      const approvedTaskId = data.id ?? data.task_id;
      if (approvedTaskId) {
        await onSubmissionApproved(approvedTaskId, data);
        await onTaskStatusChanged(approvedTaskId, "completed", data);
      }
      if (data.tx_hash) {
        ircBridge?.broadcastPaymentToIrc(data, data.tx_hash);
      }
      break;
    }

    case "submission.rejected": {
      const addr2 = data.executor_wallet ?? data.worker_wallet ?? data.worker_address;
      if (addr2) {
        await notifySubmissionRejected(addr2, data, data.reason);
      }
      const rejectedTaskId = data.id ?? data.task_id;
      if (rejectedTaskId) {
        await onSubmissionRejected(rejectedTaskId, data.reason);
      }
      break;
    }

    case "payment.settled":
    case "payment.released":
    case "disburse_worker": {
      await handlePaymentEvent({
        type: event.type,
        ...data,
      });
      break;
    }

    case "reputation.created":
    case "rating.created": {
      const target = data.target_address ?? data.to_address;
      if (target) {
        await notifyNewRating(target, {
          score: data.score,
          comment: data.comment,
          from_address: data.from_address,
          task_title: data.task_title,
        });
      }
      const ratingTaskId = data.task_id;
      if (ratingTaskId) {
        await onRatingReceived(ratingTaskId, data);
      }
      break;
    }

    case "task.status_changed": {
      const statusTaskId = data.id ?? data.task_id;
      if (statusTaskId) {
        await onTaskStatusChanged(
          statusTaskId,
          data.status ?? data.new_status,
          data,
        );
        ircBridge?.broadcastStatusToIrc(statusTaskId, data.status ?? data.new_status, data.title);
      }
      break;
    }

    case "evidence.submitted": {
      const evidenceTaskId = data.task_id;
      if (evidenceTaskId) {
        await onEvidenceSubmitted(evidenceTaskId, data);
        ircBridge?.broadcastStatusToIrc(evidenceTaskId, "submitted");
      }
      break;
    }

    default:
      logger.debug({ type: event.type }, "Unhandled WS event");
  }
}
