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

      logger.debug({ eventType: event.type }, "WS event received");
      await handleEvent(event);
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

async function handleEvent(event: any): Promise<void> {
  const data = event.data ?? event.payload;
  if (!data) return;

  switch (event.type) {
    case "task.created":
      await notifyTaskCreated(data);
      break;

    case "task.assigned": {
      const workerAddress = data.executor_wallet ?? data.worker_address;
      if (workerAddress) {
        await notifyTaskAssigned(workerAddress, data);
      }
      break;
    }

    case "submission.approved": {
      const addr = data.executor_wallet ?? data.worker_address;
      if (addr) {
        await notifySubmissionApproved(addr, data, data.tx_hash);
      }
      break;
    }

    case "submission.rejected": {
      const addr2 = data.executor_wallet ?? data.worker_address;
      if (addr2) {
        await notifySubmissionRejected(addr2, data, data.reason);
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
      break;
    }

    default:
      logger.debug({ type: event.type }, "Unhandled WS event");
  }
}
