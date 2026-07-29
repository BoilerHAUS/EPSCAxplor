/**
 * Assistant answer bubble. Renders the generated answer as Markdown (headings,
 * lists, tables, emphasis) with [SOURCE N] markers replaced by numbered source
 * badges that correspond to the citation cards below. Bubble style from the
 * design-system export's ChatBubble (assistant variant).
 *
 * Markdown is rendered with react-markdown + remark-gfm. Raw HTML in the model
 * output is skipped (skipHtml, no rehype-raw) so answer text can never inject
 * markup. The [SOURCE N] -> badge substitution runs as a small rehype plugin
 * (rehypeSourceMarkers) so markers resolve wherever they appear — paragraphs,
 * list items, table cells, or headings.
 *
 * Marker syntax mirrors the backend's citation extractor
 * (services/api/src/rag/citation_extractor.py): [SOURCE N] plus extended forms
 * like [SOURCE N, Page X], case-insensitive.
 */
import type { ComponentProps } from "react";
import ReactMarkdown, {
  type Components,
  type ExtraProps,
  type Options,
} from "react-markdown";
import remarkGfm from "remark-gfm";
import { rehypeSourceMarkers } from "./rehypeSourceMarkers";
import { SourceMarker } from "./SourceMarker";

export interface AnswerCardProps {
  answer: string;
}

// rehypeSourceMarkers injects <source-marker> elements carrying the source
// number on `dataSourceNumber`; render each as the numbered badge.
function SourceMarkerElement({ node }: ExtraProps) {
  const parsed = Number(node?.properties?.dataSourceNumber);
  if (!Number.isInteger(parsed) || parsed <= 0) return null;
  return <SourceMarker number={parsed} />;
}

// Any links in an answer open in a new tab without leaking the opener/referrer;
// react-markdown's default URL sanitiser already blocks javascript: URLs.
function Anchor({ href, children }: ComponentProps<"a"> & ExtraProps) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer nofollow">
      {children}
    </a>
  );
}

// "source-marker" is not an intrinsic HTML tag, so the map is widened to the
// react-markdown Components type past its intrinsic-element keys.
const COMPONENTS = {
  "source-marker": SourceMarkerElement,
  a: Anchor,
} as Components;

const REMARK_PLUGINS: Options["remarkPlugins"] = [remarkGfm];
const REHYPE_PLUGINS = [rehypeSourceMarkers] as Options["rehypePlugins"];

export function AnswerCard({ answer }: AnswerCardProps) {
  return (
    <article className="record">
      <div className="record__head">
        <span className="u-label">Answer</span>
        <span className="record__status u-label">Grounded</span>
      </div>
      <div className="record__body">
        <div className="markdown">
          <ReactMarkdown
            remarkPlugins={REMARK_PLUGINS}
            rehypePlugins={REHYPE_PLUGINS}
            skipHtml
            components={COMPONENTS}
          >
            {answer}
          </ReactMarkdown>
        </div>
      </div>
    </article>
  );
}
