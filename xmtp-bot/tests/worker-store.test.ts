import { describe, it, expect, beforeEach, vi } from "vitest";

// Reset module state between tests
let getWorkerStore: () => any;

beforeEach(async () => {
  vi.resetModules();
  const mod = await import("../src/services/worker-store.js");
  getWorkerStore = mod.getWorkerStore;
});

describe("WorkerStore", () => {
  it("creates a new entry for unknown address", () => {
    const store = getWorkerStore();
    const entry = store.getOrCreate("0xABC123");
    expect(entry).toBeDefined();
    expect(entry.xmtpAddress).toBe("0xabc123"); // lowercased
    expect(entry.conversationState).toBe("idle");
  });

  it("returns same entry on repeated getOrCreate", () => {
    const store = getWorkerStore();
    const a = store.getOrCreate("0xABC");
    const b = store.getOrCreate("0xabc");
    expect(a).toBe(b);
  });

  it("returns undefined for unknown address via getByAddress", () => {
    const store = getWorkerStore();
    expect(store.getByAddress("0xNONEXISTENT")).toBeUndefined();
  });

  it("registers a worker and stores executorId", () => {
    const store = getWorkerStore();
    store.register("0xABC", "exec-123", "Carlos");
    const entry = store.getByAddress("0xABC");
    expect(entry?.executorId).toBe("exec-123");
    expect(entry?.name).toBe("Carlos");
    expect(entry?.conversationState).toBe("idle");
  });

  it("tracks conversation state transitions", () => {
    const store = getWorkerStore();
    expect(store.getConversationState("0xABC")).toBe("idle");

    store.setConversationState("0xABC", "submission");
    expect(store.getConversationState("0xABC")).toBe("submission");

    store.setConversationState("0xABC", "registration");
    expect(store.getConversationState("0xABC")).toBe("registration");

    store.resetConversation("0xABC");
    expect(store.getConversationState("0xABC")).toBe("idle");
  });

  it("manages registration progress", () => {
    const store = getWorkerStore();
    store.setRegistrationProgress("0xABC", { step: "name" });
    expect(store.getRegistrationProgress("0xABC")?.step).toBe("name");
    expect(store.getConversationState("0xABC")).toBe("registration");

    store.setRegistrationProgress("0xABC", {
      step: "email",
      name: "Carlos",
    });
    expect(store.getRegistrationProgress("0xABC")?.name).toBe("Carlos");
  });

  it("lists all registered workers", () => {
    const store = getWorkerStore();
    store.register("0x001", "e1", "Alice");
    store.register("0x002", "e2", "Bob");
    store.getOrCreate("0x003"); // not registered

    const registered = store.getAllRegistered();
    expect(registered.length).toBe(2);
    expect(registered.map((w: any) => w.name).sort()).toEqual([
      "Alice",
      "Bob",
    ]);
  });

  it("resetConversation clears registration progress", () => {
    const store = getWorkerStore();
    store.setRegistrationProgress("0xABC", {
      step: "confirm",
      name: "Carlos",
      email: "c@x.com",
    });
    store.resetConversation("0xABC");
    expect(store.getRegistrationProgress("0xABC")).toBeUndefined();
    expect(store.getConversationState("0xABC")).toBe("idle");
  });
});
