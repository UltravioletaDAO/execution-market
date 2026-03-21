import { describe, it, expect } from "vitest";
import {
  markdownToIrc,
  ircToMarkdown,
  truncateForIrc,
  formatTaskForIrc,
  formatStatusForIrc,
} from "../src/bridges/formatters.js";

describe("markdownToIrc", () => {
  it("strips bold markers", () => {
    expect(markdownToIrc("**hello**")).toBe("hello");
  });

  it("strips italic markers", () => {
    expect(markdownToIrc("_world_")).toBe("world");
  });

  it("strips inline code markers", () => {
    expect(markdownToIrc("`code here`")).toBe("code here");
  });

  it("converts links to text (url) format", () => {
    expect(markdownToIrc("[click here](https://example.com)")).toBe(
      "click here (https://example.com)",
    );
  });

  it("collapses multiple blank lines", () => {
    const input = "line1\n\n\n\n\nline2";
    expect(markdownToIrc(input)).toBe("line1\n\nline2");
  });

  it("handles combined markdown", () => {
    const md = "**Bold** and _italic_ with `code` and [link](https://x.com)";
    const result = markdownToIrc(md);
    expect(result).toBe("Bold and italic with code and link (https://x.com)");
  });
});

describe("ircToMarkdown", () => {
  it("adds nick as bold prefix", () => {
    const result = ircToMarkdown("hello!", "alice");
    expect(result).toBe("**[alice]** hello!");
  });

  it("linkifies URLs", () => {
    const result = ircToMarkdown("check https://example.com out", "bob");
    expect(result).toContain("[https://example.com](https://example.com)");
  });

  it("highlights IRC commands", () => {
    const result = ircToMarkdown("use /claim to apply", "bob");
    expect(result).toContain("`/claim`");
  });
});

describe("truncateForIrc", () => {
  it("returns short text as-is", () => {
    expect(truncateForIrc("hello")).toBe("hello");
  });

  it("truncates long text", () => {
    const long = "x".repeat(500);
    const result = truncateForIrc(long);
    expect(result.length).toBe(450);
    expect(result.endsWith("...")).toBe(true);
  });

  it("respects custom maxLen", () => {
    const long = "x".repeat(100);
    const result = truncateForIrc(long, 50);
    expect(result.length).toBe(50);
  });
});

describe("formatTaskForIrc", () => {
  it("formats basic task", () => {
    const task = {
      id: "abcdef12-3456-7890-abcd-ef1234567890",
      title: "Take photo of store",
      bounty_usdc: 0.5,
      payment_network: "base",
      category: "physical_presence",
    };
    const result = formatTaskForIrc(task);
    expect(result).toContain("[NEW TASK]");
    expect(result).toContain("Take photo of store");
    expect(result).toContain("$0.50 USDC");
    expect(result).toContain("base");
    expect(result).toContain("physical_presence");
    expect(result).toContain("/claim abcdef12");
  });

  it("handles missing fields gracefully", () => {
    const task = { id: "1234567890" };
    const result = formatTaskForIrc(task);
    expect(result).toContain("[NEW TASK]");
    expect(result).toContain("$0.00 USDC");
    expect(result).toContain("general");
  });

  it("truncates long titles", () => {
    const task = {
      id: "abcdef1234567890",
      title: "A".repeat(200),
      bounty: 1,
    };
    const result = formatTaskForIrc(task);
    // Title truncated to 80 chars
    expect(result.length).toBeLessThan(300);
  });
});

describe("formatStatusForIrc", () => {
  it("formats accepted status", () => {
    const result = formatStatusForIrc("abcdef1234567890", "accepted", "Photo task");
    expect(result).toBe("[ASSIGNED] Task abcdef12 | Photo task");
  });

  it("formats completed status", () => {
    const result = formatStatusForIrc("abcdef1234567890", "completed");
    expect(result).toBe("[COMPLETED] Task abcdef12");
  });

  it("formats submitted status", () => {
    const result = formatStatusForIrc("abcdef1234567890", "submitted");
    expect(result).toBe("[EVIDENCE SUBMITTED] Task abcdef12");
  });

  it("handles unknown status", () => {
    const result = formatStatusForIrc("abcdef1234567890", "custom_thing");
    expect(result).toBe("[CUSTOM_THING] Task abcdef12");
  });
});
