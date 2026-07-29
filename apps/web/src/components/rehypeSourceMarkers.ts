/**
 * rehype plugin: split text nodes containing [SOURCE N] citation markers into
 * text + a <source-marker> element carrying the source number, so AnswerCard can
 * render each marker as a numbered SourceMarker badge wherever it appears in the
 * answer — paragraphs, list items, table cells, or headings. Centralising the
 * substitution here (rather than per element type) means every text node in the
 * Markdown tree is handled exactly once.
 *
 * Marker syntax mirrors the backend citation extractor
 * (services/api/src/rag/citation_extractor.py): [SOURCE N] plus extended forms
 * like [SOURCE N, Page X], case-insensitive.
 *
 * The transform is pure — the input tree is never mutated; new node arrays are
 * returned throughout.
 */

/** Minimal structural view of the hast nodes this plugin touches. */
export interface HastText {
  type: "text";
  value: string;
}

export interface HastElement {
  type: "element";
  tagName: string;
  properties?: Record<string, unknown>;
  children: HastNode[];
}

export type HastNode = HastText | HastElement | { type: string; children?: HastNode[] };

export interface HastRoot {
  type: "root";
  children: HastNode[];
}

/** Tag name of the injected marker element; mapped to SourceMarker in AnswerCard. */
export const SOURCE_MARKER_TAG = "source-marker";

const SOURCE_PATTERN = /\[SOURCE\s+(\d+)[^\]]*\]/gi;

function isText(node: HastNode): node is HastText {
  return node.type === "text" && typeof (node as HastText).value === "string";
}

function isElement(node: HastNode): node is HastElement {
  return node.type === "element" && Array.isArray((node as HastElement).children);
}

/** Split one text node into text + marker element nodes; unchanged if no markers. */
function splitText(node: HastText): HastNode[] {
  const { value } = node;
  const out: HastNode[] = [];
  let lastIndex = 0;
  for (const match of value.matchAll(SOURCE_PATTERN)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      out.push({ type: "text", value: value.slice(lastIndex, index) });
    }
    out.push({
      type: "element",
      tagName: SOURCE_MARKER_TAG,
      properties: { dataSourceNumber: match[1] },
      children: [],
    });
    lastIndex = index + match[0].length;
  }
  if (out.length === 0) return [node];
  if (lastIndex < value.length) {
    out.push({ type: "text", value: value.slice(lastIndex) });
  }
  return out;
}

function transformChildren(children: HastNode[]): HastNode[] {
  return children.flatMap((child) => {
    if (isText(child)) return splitText(child);
    if (isElement(child)) return [{ ...child, children: transformChildren(child.children) }];
    return [child];
  });
}

export function rehypeSourceMarkers() {
  return (tree: HastRoot): HastRoot => ({
    ...tree,
    children: transformChildren(tree.children),
  });
}
