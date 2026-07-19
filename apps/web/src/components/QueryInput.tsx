"use client";

/**
 * Query composer: textarea (Enter submits, Shift+Enter for a newline)
 * + send button (from the design-system export's ChatComposer) with an
 * optional union filter.
 *
 * POST /query accepts only { query } — the backend derives union filters
 * by detecting canonical union names in the query text
 * (services/api/src/rag/preprocess.py). Selecting a union therefore
 * prefixes the submitted text with "<Union>: " unless the query already
 * names it. A document-type filter is not possible with the current
 * /query contract (no such parameter, and preprocessing does not detect
 * document types), so it is intentionally not offered.
 */
import { useState, type KeyboardEvent } from "react";

export interface QueryInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
  /** Canonical union names (from the corpus registry) for the filter. */
  unions: string[];
  placeholder?: string;
}

const ALL_UNIONS = "";

export function QueryInput({
  onSubmit,
  disabled = false,
  unions,
  placeholder = "Ask about overtime, wages, nuclear provisions…",
}: QueryInputProps) {
  const [value, setValue] = useState("");
  const [union, setUnion] = useState<string>(ALL_UNIONS);

  function submit() {
    const query = value.trim();
    if (disabled || !query) return;
    const needsPrefix =
      union !== ALL_UNIONS && !query.toLowerCase().includes(union.toLowerCase());
    onSubmit(needsPrefix ? `${union}: ${query}` : query);
    setValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {unions.length > 0 ? (
        <select
          aria-label="Union filter"
          value={union}
          disabled={disabled}
          onChange={(e) => setUnion(e.target.value)}
          className="scope-select"
          style={{ opacity: disabled ? 0.5 : 1 }}
        >
          <option value={ALL_UNIONS}>All unions</option>
          {unions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      ) : null}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="composer"
      >
        <span className="composer__marker" aria-hidden="true">
          ›
        </span>
        <textarea
          value={value}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="composer__field"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send"
          className="composer__send"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}
