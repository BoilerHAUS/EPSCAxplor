import { describe, expect, it } from "vitest";
import {
  type HastElement,
  type HastNode,
  type HastRoot,
  rehypeSourceMarkers,
} from "./rehypeSourceMarkers";

const text = (value: string): HastNode => ({ type: "text", value });
const element = (tagName: string, children: HastNode[]): HastElement => ({
  type: "element",
  tagName,
  properties: {},
  children,
});
const root = (children: HastNode[]): HastRoot => ({ type: "root", children });

const markerNumbers = (nodes: HastNode[]): unknown[] =>
  nodes
    .filter((n): n is HastElement => n.type === "element" && (n as HastElement).tagName === "source-marker")
    .map((n) => n.properties?.dataSourceNumber);

describe("rehypeSourceMarkers", () => {
  it("splits a [SOURCE N] marker in a text node into text + marker element", () => {
    const out = rehypeSourceMarkers()(root([element("p", [text("Rate is high [SOURCE 3] today")])]));
    const paragraph = out.children[0] as HastElement;

    expect(paragraph.children).toHaveLength(3);
    expect(paragraph.children[0]).toEqual(text("Rate is high "));
    expect(paragraph.children[1]).toMatchObject({
      type: "element",
      tagName: "source-marker",
      properties: { dataSourceNumber: "3" },
    });
    expect(paragraph.children[2]).toEqual(text(" today"));
  });

  it("leaves text without markers unchanged", () => {
    const out = rehypeSourceMarkers()(root([element("p", [text("no markers here")])]));
    const paragraph = out.children[0] as HastElement;
    expect(paragraph.children[0]).toEqual(text("no markers here"));
  });

  it("handles extended marker forms and multiple markers in one node", () => {
    const out = rehypeSourceMarkers()(
      root([element("p", [text("a [SOURCE 1] b [SOURCE 2, Page 5] c")])]),
    );
    const paragraph = out.children[0] as HastElement;
    expect(markerNumbers(paragraph.children)).toEqual(["1", "2"]);
  });

  it("recurses into nested elements (markers inside list items)", () => {
    const out = rehypeSourceMarkers()(
      root([element("ul", [element("li", [text("x [SOURCE 9]")])])]),
    );
    const list = out.children[0] as HastElement;
    const item = list.children[0] as HastElement;
    expect(markerNumbers(item.children)).toEqual(["9"]);
  });

  it("does not mutate the input tree", () => {
    const input = root([element("p", [text("a [SOURCE 1] b")])]);
    const snapshot = JSON.parse(JSON.stringify(input));
    rehypeSourceMarkers()(input);
    expect(input).toEqual(snapshot);
  });
});
