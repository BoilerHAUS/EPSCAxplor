import { describe, expect, it } from "vitest";
import { isSafeHttpUrl } from "./isSafeHttpUrl";

describe("isSafeHttpUrl", () => {
  it("accepts https URLs", () => {
    expect(isSafeHttpUrl("https://www.epsca.org/upload/request/5?file=IBEW.pdf&download=1")).toBe(
      true,
    );
  });

  it("accepts http URLs", () => {
    expect(isSafeHttpUrl("http://www.epsca.org/x.pdf")).toBe(true);
  });

  it("normalises an uppercase scheme", () => {
    expect(isSafeHttpUrl("HTTPS://www.epsca.org/x.pdf")).toBe(true);
  });

  it("rejects null and undefined", () => {
    expect(isSafeHttpUrl(null)).toBe(false);
    expect(isSafeHttpUrl(undefined)).toBe(false);
  });

  it("rejects empty and whitespace-only strings", () => {
    expect(isSafeHttpUrl("")).toBe(false);
    expect(isSafeHttpUrl("   ")).toBe(false);
  });

  it("rejects the PLACEHOLDER sentinel (defense against un-normalised legacy rows)", () => {
    expect(isSafeHttpUrl("PLACEHOLDER")).toBe(false);
  });

  it("rejects the javascript: scheme (XSS guard)", () => {
    expect(isSafeHttpUrl("javascript:alert(1)")).toBe(false);
  });

  it("rejects the data: scheme", () => {
    expect(isSafeHttpUrl("data:text/html,<script>alert(1)</script>")).toBe(false);
  });

  it("rejects relative paths", () => {
    expect(isSafeHttpUrl("/corpus/ibew.pdf")).toBe(false);
  });

  it("rejects a scheme with no host", () => {
    expect(isSafeHttpUrl("http://")).toBe(false);
  });
});
