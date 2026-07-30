/**
 * Guard for rendering an externally-sourced URL as a link.
 *
 * Corpus `source_url` values are external and nullable ("PLACEHOLDER"/null for
 * manually-downloaded docs). Only http(s) URLs are safe to render as an anchor —
 * this rejects null/empty, the "PLACEHOLDER" sentinel, relative paths, and unsafe
 * schemes (`javascript:`, `data:`) so a stored value can never become a dead or
 * script-bearing link. Uses the platform URL parser (same primitive as csp.ts).
 *
 * Also usable by #169 (deep-link answer citations).
 */
export function isSafeHttpUrl(value: string | null | undefined): value is string {
  if (!value) return false;
  try {
    const { protocol } = new URL(value);
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}
