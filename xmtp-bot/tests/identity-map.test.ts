import { describe, it, expect, beforeEach, vi } from "vitest";

let linkNickToWallet: any;
let getWalletByNick: any;
let getNickByWallet: any;
let unlinkNick: any;
let getAllLinks: any;
let isValidEthAddress: any;

beforeEach(async () => {
  vi.resetModules();
  const mod = await import("../src/bridges/identity-map.js");
  linkNickToWallet = mod.linkNickToWallet;
  getWalletByNick = mod.getWalletByNick;
  getNickByWallet = mod.getNickByWallet;
  unlinkNick = mod.unlinkNick;
  getAllLinks = mod.getAllLinks;
  isValidEthAddress = mod.isValidEthAddress;
});

describe("Identity Map", () => {
  const NICK = "testuser";
  const WALLET = "0x1234567890abcdef1234567890abcdef12345678";

  it("links nick to wallet and looks up both directions", () => {
    linkNickToWallet(NICK, WALLET);
    expect(getWalletByNick(NICK)).toBe(WALLET.toLowerCase());
    expect(getNickByWallet(WALLET)).toBe(NICK.toLowerCase());
  });

  it("is case-insensitive", () => {
    linkNickToWallet("TestUser", WALLET.toUpperCase());
    expect(getWalletByNick("testuser")).toBe(WALLET.toLowerCase());
    expect(getWalletByNick("TESTUSER")).toBe(WALLET.toLowerCase());
    expect(getNickByWallet(WALLET.toLowerCase())).toBe("testuser");
  });

  it("returns undefined for unlinked nick", () => {
    expect(getWalletByNick("nobody")).toBeUndefined();
    expect(getNickByWallet("0x" + "0".repeat(40))).toBeUndefined();
  });

  it("replaces old mapping when nick re-links", () => {
    const wallet2 = "0x" + "a".repeat(40);
    linkNickToWallet(NICK, WALLET);
    linkNickToWallet(NICK, wallet2);

    expect(getWalletByNick(NICK)).toBe(wallet2.toLowerCase());
    // Old wallet should be unlinked
    expect(getNickByWallet(WALLET)).toBeUndefined();
  });

  it("replaces old mapping when wallet re-links to different nick", () => {
    linkNickToWallet("alice", WALLET);
    linkNickToWallet("bob", WALLET);

    expect(getWalletByNick("bob")).toBe(WALLET.toLowerCase());
    expect(getWalletByNick("alice")).toBeUndefined();
    expect(getNickByWallet(WALLET)).toBe("bob");
  });

  it("unlinks nick", () => {
    linkNickToWallet(NICK, WALLET);
    expect(unlinkNick(NICK)).toBe(true);
    expect(getWalletByNick(NICK)).toBeUndefined();
    expect(getNickByWallet(WALLET)).toBeUndefined();
  });

  it("returns false when unlinking non-existent nick", () => {
    expect(unlinkNick("nobody")).toBe(false);
  });

  it("getAllLinks returns linked entries", () => {
    linkNickToWallet("alice", "0x" + "a".repeat(40));
    linkNickToWallet("bob", "0x" + "b".repeat(40));
    const links = getAllLinks();
    expect(links.length).toBe(2);
    expect(links.map((l: any) => l.nick).sort()).toEqual(["alice", "bob"]);
  });
});

describe("isValidEthAddress", () => {
  it("accepts valid checksummed address", () => {
    expect(isValidEthAddress("0x1234567890abcdef1234567890abcdef12345678")).toBe(
      true,
    );
  });

  it("accepts uppercase hex", () => {
    expect(isValidEthAddress("0xABCDEF1234567890ABCDEF1234567890ABCDEF12")).toBe(
      true,
    );
  });

  it("rejects address without 0x prefix", () => {
    expect(isValidEthAddress("1234567890abcdef1234567890abcdef12345678")).toBe(
      false,
    );
  });

  it("rejects short address", () => {
    expect(isValidEthAddress("0x1234")).toBe(false);
  });

  it("rejects address with invalid chars", () => {
    expect(isValidEthAddress("0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG")).toBe(
      false,
    );
  });

  it("rejects empty string", () => {
    expect(isValidEthAddress("")).toBe(false);
  });
});
