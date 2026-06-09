/**
 * Tests for the OWS spending-policy engine (L-82).
 *
 * Run: npx tsx --test src/spending-policy.test.ts
 *
 * These reproduce the vulnerability: before the policy existed, an unbounded
 * EIP-3009 USDC authorization for any amount to any recipient was signed. The
 * tests assert that an over-limit / disallowed authorization is now rejected,
 * and that legitimate in-limit authorizations still pass.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  loadSpendingPolicy,
  evaluateSpend,
  recordSpend,
  extractUsdcTransferFromTypedData,
  _resetSpendLog,
} from "./spending-policy.js";

const WORKER = "0x1111111111111111111111111111111111111111";
const OTHER = "0x2222222222222222222222222222222222222222";

function clearEnv() {
  delete process.env.OWS_SPENDING_POLICY_ENABLED;
  delete process.env.OWS_MAX_AMOUNT_USDC_PER_TX;
  delete process.env.OWS_ALLOWED_RECIPIENTS;
  delete process.env.OWS_DAILY_LIMIT_USDC;
  _resetSpendLog();
}

test("secure default: policy enabled with a finite per-tx cap", () => {
  clearEnv();
  const p = loadSpendingPolicy();
  assert.equal(p.enabled, true, "policy must default to ENABLED");
  assert.ok(p.maxPerTxUsdc > 0 && Number.isFinite(p.maxPerTxUsdc));
});

test("REPRO L-82: an over-limit USDC authorization is REJECTED", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "100";
  // Pre-fix behaviour signed any amount; the drain auth here is 100_000 USDC.
  const decision = evaluateSpend(100_000, WORKER);
  assert.equal(decision.allowed, false);
  assert.match(decision.reason ?? "", /per-transaction limit/);
});

test("an in-limit authorization is allowed", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "100";
  const decision = evaluateSpend(0.1, WORKER);
  assert.equal(decision.allowed, true);
});

test("amount exactly at the cap is allowed; just over is rejected", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "50";
  assert.equal(evaluateSpend(50, WORKER).allowed, true);
  assert.equal(evaluateSpend(50.000001, WORKER).allowed, false);
});

test("zero / NaN amounts are rejected", () => {
  clearEnv();
  assert.equal(evaluateSpend(0, WORKER).allowed, false);
  assert.equal(evaluateSpend(Number.NaN, WORKER).allowed, false);
  assert.equal(evaluateSpend(-5, WORKER).allowed, false);
});

test("recipient allowlist: in-list passes, out-of-list rejected", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "100";
  process.env.OWS_ALLOWED_RECIPIENTS = WORKER.toUpperCase(); // case-insensitive
  assert.equal(evaluateSpend(1, WORKER).allowed, true);
  const rej = evaluateSpend(1, OTHER);
  assert.equal(rej.allowed, false);
  assert.match(rej.reason ?? "", /allowlist/);
});

test("rolling 24h cap: accumulates and blocks once exceeded", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "100";
  process.env.OWS_DAILY_LIMIT_USDC = "10";
  const now = Date.now();
  // First two 4-USDC spends are fine (8 total), recorded as committed.
  assert.equal(evaluateSpend(4, WORKER, undefined, now).allowed, true);
  recordSpend(4, now);
  assert.equal(evaluateSpend(4, WORKER, undefined, now).allowed, true);
  recordSpend(4, now);
  // A third 4-USDC spend would push to 12 > 10 → rejected.
  const rej = evaluateSpend(4, WORKER, undefined, now);
  assert.equal(rej.allowed, false);
  assert.match(rej.reason ?? "", /daily limit/);
});

test("rolling cap forgets spends older than 24h", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "100";
  process.env.OWS_DAILY_LIMIT_USDC = "10";
  const now = Date.now();
  recordSpend(9, now - 25 * 60 * 60 * 1000); // 25h ago → expired
  // Fresh budget should be available again.
  assert.equal(evaluateSpend(9, WORKER, undefined, now).allowed, true);
});

test("disabled policy allows anything (explicit opt-out)", () => {
  clearEnv();
  process.env.OWS_SPENDING_POLICY_ENABLED = "false";
  assert.equal(evaluateSpend(1_000_000, OTHER).allowed, true);
});

test("REPRO L-82 bypass: typed-data TransferWithAuthorization is policy-checked", () => {
  clearEnv();
  process.env.OWS_MAX_AMOUNT_USDC_PER_TX = "100";
  // 1,000,000 USDC = 1_000_000 * 1e6 base units.
  const typedData = {
    primaryType: "TransferWithAuthorization",
    message: {
      from: OTHER,
      to: WORKER,
      value: (1_000_000n * 1_000_000n).toString(),
    },
  };
  const extracted = extractUsdcTransferFromTypedData(typedData);
  assert.ok(extracted, "should extract a USDC transfer");
  assert.equal(extracted!.amountUsdc, 1_000_000);
  assert.equal(extracted!.to, WORKER);
  const decision = evaluateSpend(extracted!.amountUsdc, extracted!.to);
  assert.equal(decision.allowed, false);
});

test("typed-data extraction returns null for non-transfer messages", () => {
  clearEnv();
  // ERC-8128 / permit style message — must NOT be treated as a USDC transfer.
  const permit = {
    primaryType: "Permit",
    message: { owner: OTHER, spender: WORKER, value: "123" },
  };
  assert.equal(extractUsdcTransferFromTypedData(permit), null);
  assert.equal(extractUsdcTransferFromTypedData("not json"), null);
  assert.equal(extractUsdcTransferFromTypedData(null), null);
});

test("ReceiveWithAuthorization is also extracted (escrow deposit path)", () => {
  clearEnv();
  const td = {
    primaryType: "ReceiveWithAuthorization",
    message: { to: WORKER, value: (5n * 1_000_000n).toString() },
  };
  const extracted = extractUsdcTransferFromTypedData(td);
  assert.ok(extracted);
  assert.equal(extracted!.amountUsdc, 5);
});
