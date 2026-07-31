import { describe, expect, it } from "vitest";
import { citationSourceHref } from "./citationSourceHref";

const URL = "https://www.epsca.org/upload/request/5?file=IBEW.pdf&download=1";

describe("citationSourceHref", () => {
  it("appends a #page anchor when a page number is present", () => {
    expect(citationSourceHref(URL, 21)).toBe(`${URL}#page=21`);
  });

  it("returns the bare URL when there is no page number", () => {
    expect(citationSourceHref(URL, null)).toBe(URL);
  });

  it("ignores a non-positive or non-integer page number", () => {
    expect(citationSourceHref(URL, 0)).toBe(URL);
    expect(citationSourceHref(URL, -3)).toBe(URL);
    expect(citationSourceHref(URL, 1.5)).toBe(URL);
  });

  it("returns null for a null or undefined source url", () => {
    expect(citationSourceHref(null, 21)).toBeNull();
    expect(citationSourceHref(undefined, 21)).toBeNull();
  });

  it("returns null for an unsafe scheme (XSS guard)", () => {
    expect(citationSourceHref("javascript:alert(1)", 21)).toBeNull();
  });

  it("returns null for the PLACEHOLDER sentinel", () => {
    expect(citationSourceHref("PLACEHOLDER", 21)).toBeNull();
  });
});
