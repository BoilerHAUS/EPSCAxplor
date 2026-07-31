import { isSafeHttpUrl } from "./isSafeHttpUrl";

/**
 * Build a safe deep-link href for a cited source document (#169).
 *
 * Returns the source URL with a `#page=N` PDF anchor when a positive page number
 * is known, the bare URL when it is not, or null when the source is missing or
 * not a safe http(s) URL (so the caller renders no link). Reuses isSafeHttpUrl,
 * so unsafe schemes (`javascript:`, `data:`), relative paths, and the
 * "PLACEHOLDER" sentinel can never become a link.
 */
export function citationSourceHref(
  sourceUrl: string | null | undefined,
  pageNumber: number | null | undefined,
): string | null {
  if (!isSafeHttpUrl(sourceUrl)) {
    return null;
  }
  if (pageNumber != null && Number.isInteger(pageNumber) && pageNumber > 0) {
    return `${sourceUrl}#page=${pageNumber}`;
  }
  return sourceUrl;
}
