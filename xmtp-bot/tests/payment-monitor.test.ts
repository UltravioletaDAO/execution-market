import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock agent ───────────────────────────────────────────────

const mockDm = {
  sendText: vi.fn().mockResolvedValue(undefined),
  sendTransactionReference: vi.fn().mockResolvedValue(undefined),
};

const mockAgent = {
  createDmWithAddress: vi.fn().mockResolvedValue(mockDm),
};

vi.mock("../src/agent.js", () => ({
  getAgent: () => mockAgent,
}));

vi.mock("../src/utils/formatters.js", () => ({
  formatUsdc: (v: number | string) => {
    const n = typeof v === "string" ? parseFloat(v) : v;
    return n.toFixed(2);
  },
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

import { handlePaymentEvent, txLink } from "../src/services/payment-monitor.js";

describe("payment-monitor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("txLink", () => {
    it("returns basescan link for base", () => {
      expect(txLink("base", "0xabc")).toBe("https://basescan.org/tx/0xabc");
    });

    it("returns etherscan link for ethereum", () => {
      expect(txLink("ethereum", "0xdef")).toBe("https://etherscan.io/tx/0xdef");
    });

    it("returns polygonscan link for polygon", () => {
      expect(txLink("polygon", "0x123")).toBe("https://polygonscan.com/tx/0x123");
    });

    it("returns arbiscan for arbitrum", () => {
      expect(txLink("arbitrum", "0x456")).toBe("https://arbiscan.io/tx/0x456");
    });

    it("returns snowtrace for avalanche", () => {
      expect(txLink("avalanche", "0x789")).toBe("https://snowtrace.io/tx/0x789");
    });

    it("returns optimistic etherscan for optimism", () => {
      expect(txLink("optimism", "0xopt")).toBe(
        "https://optimistic.etherscan.io/tx/0xopt",
      );
    });

    it("returns celoscan for celo", () => {
      expect(txLink("celo", "0xcel")).toBe("https://celoscan.io/tx/0xcel");
    });

    it("returns monad explorer for monad", () => {
      expect(txLink("monad", "0xmon")).toBe(
        "https://explorer.monad.xyz/tx/0xmon",
      );
    });

    it("falls back to blockscan for unknown chains", () => {
      expect(txLink("fantom", "0xftm")).toBe(
        "https://blockscan.com/tx/0xftm",
      );
    });
  });

  describe("handlePaymentEvent", () => {
    it("sends markdown receipt + TX reference for base payment", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWorker",
        tx_hash: "0xHash123",
        amount: "5.00",
        chain: "base",
        task_title: "Buy coffee",
      });

      expect(mockAgent.createDmWithAddress).toHaveBeenCalledWith("0xWorker");
      expect(mockDm.sendText).toHaveBeenCalledWith(
        expect.stringContaining("Pago Recibido"),
      );
      expect(mockDm.sendText).toHaveBeenCalledWith(
        expect.stringContaining("5.00 USDC"),
      );
      expect(mockDm.sendText).toHaveBeenCalledWith(
        expect.stringContaining("basescan.org"),
      );
      expect(mockDm.sendTransactionReference).toHaveBeenCalledWith(
        expect.objectContaining({
          namespace: "eip155",
          networkId: "eip155:8453",
          reference: "0xHash123",
          metadata: expect.objectContaining({
            currency: "USDC",
            amount: 5.0,
            toAddress: "0xWorker",
          }),
        }),
      );
    });

    it("uses executor_wallet as fallback for worker_address", async () => {
      await handlePaymentEvent({
        type: "disburse_worker",
        executor_wallet: "0xExec",
        tx_hash: "0xHash456",
        amount: 3.0,
        chain: "polygon",
      });

      expect(mockAgent.createDmWithAddress).toHaveBeenCalledWith("0xExec");
      expect(mockDm.sendTransactionReference).toHaveBeenCalledWith(
        expect.objectContaining({
          networkId: "eip155:137",
        }),
      );
    });

    it("uses payment_network as fallback for chain", async () => {
      await handlePaymentEvent({
        type: "payment.released",
        worker_address: "0xWPN",
        tx_hash: "0xHashPN",
        amount: "2.50",
        payment_network: "arbitrum",
      });

      expect(mockDm.sendText).toHaveBeenCalledWith(
        expect.stringContaining("arbiscan.io"),
      );
    });

    it("defaults to base chain when neither chain nor payment_network", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWDef",
        tx_hash: "0xHashDefault",
        amount: 1.0,
      });

      expect(mockDm.sendTransactionReference).toHaveBeenCalledWith(
        expect.objectContaining({
          networkId: "eip155:8453",
        }),
      );
    });

    it("does nothing when no worker address", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        tx_hash: "0xNoWorker",
        amount: 1.0,
      });

      expect(mockAgent.createDmWithAddress).not.toHaveBeenCalled();
    });

    it("does nothing when no tx_hash", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWNoTx",
        amount: 1.0,
      });

      expect(mockAgent.createDmWithAddress).not.toHaveBeenCalled();
    });

    it("deduplicates same tx_hash", async () => {
      const uniqueHash = `0xDedup_${Date.now()}`;

      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWDup",
        tx_hash: uniqueHash,
        amount: 1.0,
      });

      await handlePaymentEvent({
        type: "payment.released",
        worker_address: "0xWDup",
        tx_hash: uniqueHash,
        amount: 1.0,
      });

      // Only sent once
      expect(mockAgent.createDmWithAddress).toHaveBeenCalledTimes(1);
    });

    it("shows ? for missing amount", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWNoAmt",
        tx_hash: `0xNoAmt_${Date.now()}`,
      });

      expect(mockDm.sendText).toHaveBeenCalledWith(
        expect.stringContaining("$?"),
      );
    });

    it("shows task_id when no task_title", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWTid",
        tx_hash: `0xTid_${Date.now()}`,
        amount: 1.0,
        task_id: "task-999",
      });

      expect(mockDm.sendText).toHaveBeenCalledWith(
        expect.stringContaining("task-999"),
      );
    });

    it("skips TX reference for unknown CAIP-2 chain", async () => {
      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWUnk",
        tx_hash: `0xUnk_${Date.now()}`,
        amount: 1.0,
        chain: "fantom",
      });

      expect(mockDm.sendText).toHaveBeenCalled();
      expect(mockDm.sendTransactionReference).not.toHaveBeenCalled();
    });

    it("handles agent error gracefully", async () => {
      mockAgent.createDmWithAddress.mockRejectedValueOnce(
        new Error("XMTP error"),
      );

      await handlePaymentEvent({
        type: "payment.settled",
        worker_address: "0xWErr",
        tx_hash: `0xErr_${Date.now()}`,
        amount: 1.0,
      });

      // Should not throw
    });
  });
});
