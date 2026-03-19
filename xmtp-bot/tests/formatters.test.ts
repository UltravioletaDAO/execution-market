import { describe, it, expect } from "vitest";
import {
  formatUsdc,
  formatDeadline,
  shortId,
  truncate,
  txLink,
  chainName,
  chainToCaip2,
  formatPaymentReceipt,
} from "../src/utils/formatters.js";

describe("formatUsdc", () => {
  it("formats integer", () => {
    expect(formatUsdc(5)).toBe("5.00");
  });

  it("formats decimal", () => {
    expect(formatUsdc(1.5)).toBe("1.50");
  });

  it("formats string input", () => {
    expect(formatUsdc("0.123456")).toBe("0.12");
  });

  it("handles zero", () => {
    expect(formatUsdc(0)).toBe("0.00");
  });

  it("handles large numbers", () => {
    expect(formatUsdc(99999.999)).toBe("100000.00");
  });
});

describe("formatDeadline", () => {
  it("returns Expirado for past dates", () => {
    const past = new Date(Date.now() - 1000).toISOString();
    expect(formatDeadline(past)).toBe("Expirado");
  });

  it("returns minutes for near future", () => {
    const soon = new Date(Date.now() + 30 * 60_000).toISOString();
    expect(formatDeadline(soon)).toMatch(/^\d+m$/);
  });

  it("returns hours+minutes for hours away", () => {
    const hours = new Date(Date.now() + 3 * 3_600_000 + 15 * 60_000).toISOString();
    expect(formatDeadline(hours)).toMatch(/^\d+h \d+m$/);
  });

  it("returns days for far future", () => {
    const days = new Date(Date.now() + 3 * 86_400_000).toISOString();
    expect(formatDeadline(days)).toMatch(/^\d+d \d+h$/);
  });
});

describe("shortId", () => {
  it("returns first 8 chars", () => {
    expect(shortId("abcdefgh12345678")).toBe("abcdefgh");
  });

  it("handles UUID", () => {
    expect(shortId("550e8400-e29b-41d4-a716-446655440000")).toBe("550e8400");
  });
});

describe("truncate", () => {
  it("returns short text as-is", () => {
    expect(truncate("hello", 100)).toBe("hello");
  });

  it("truncates long text with ellipsis", () => {
    const long = "a".repeat(200);
    const result = truncate(long, 50);
    expect(result.length).toBe(50);
    expect(result.endsWith("...")).toBe(true);
  });

  it("uses default maxLen of 100", () => {
    const long = "a".repeat(200);
    const result = truncate(long);
    expect(result.length).toBe(100);
  });
});

describe("txLink", () => {
  const hash = "0xabc123def456";

  it("generates Base link", () => {
    expect(txLink("base", hash)).toBe(`https://basescan.org/tx/${hash}`);
  });

  it("generates Ethereum link", () => {
    expect(txLink("ethereum", hash)).toBe(`https://etherscan.io/tx/${hash}`);
  });

  it("generates Polygon link", () => {
    expect(txLink("polygon", hash)).toBe(`https://polygonscan.com/tx/${hash}`);
  });

  it("generates Arbitrum link", () => {
    expect(txLink("arbitrum", hash)).toBe(`https://arbiscan.io/tx/${hash}`);
  });

  it("falls back to blockscan for unknown chain", () => {
    expect(txLink("unknownchain", hash)).toBe(
      `https://blockscan.com/tx/${hash}`,
    );
  });
});

describe("chainName", () => {
  it("maps known chains", () => {
    expect(chainName("base")).toBe("Base");
    expect(chainName("ethereum")).toBe("Ethereum");
    expect(chainName("polygon")).toBe("Polygon");
    expect(chainName("arbitrum")).toBe("Arbitrum");
  });

  it("returns raw for unknown chain", () => {
    expect(chainName("solana")).toBe("solana");
  });
});

describe("chainToCaip2", () => {
  it("maps Base correctly", () => {
    expect(chainToCaip2("base")).toBe("eip155:8453");
  });

  it("maps Ethereum correctly", () => {
    expect(chainToCaip2("ethereum")).toBe("eip155:1");
  });

  it("returns undefined for unknown", () => {
    expect(chainToCaip2("bitcoin")).toBeUndefined();
  });
});

describe("formatPaymentReceipt", () => {
  it("includes all key fields", () => {
    const receipt = formatPaymentReceipt({
      amount: 1.5,
      chain: "base",
      txHash: "0x" + "a".repeat(64),
      taskTitle: "Test Task",
      workerShare: 1.305,
    });
    expect(receipt).toContain("$1.50 USDC");
    expect(receipt).toContain("$1.30 USDC"); // workerShare formatted to 2dp
    expect(receipt).toContain("Base");
    expect(receipt).toContain("Test Task");
    expect(receipt).toContain("basescan.org");
  });

  it("omits worker share when not provided", () => {
    const receipt = formatPaymentReceipt({
      amount: 5,
      chain: "polygon",
      txHash: "0x" + "b".repeat(64),
    });
    expect(receipt).toContain("$5.00 USDC");
    // "Pago Recibido" is the title, so check for the table row specifically
    expect(receipt).not.toContain("Recibido (87%)");
  });
});
