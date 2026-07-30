/**
 * Build the API `history` payload from rendered chat messages (#167).
 *
 * Only completed user→answer exchanges become turns, so the result is strictly
 * user/assistant alternating, user-first, and assistant-last — exactly the shape
 * the API boundary validates (services/api/src/routes/query.py). Errored and
 * unanswered questions are dropped. The most recent exchanges are kept within
 * both the turn-count and total-character budgets, so the client never sends a
 * history the server would reject with 422.
 */
import type { ChatTurn } from "./types";

// Bounds mirror the API (services/api/src/rag/condense.py); keep them in sync.
export const MAX_HISTORY_TURNS = 6;
export const PER_TURN_CHAR_CAP = 4000;
export const TOTAL_HISTORY_CHAR_BUDGET = 12000;

/** Minimal view of a rendered chat message needed to derive API history. */
export type HistoryMessage =
  | { kind: "user"; text: string }
  | { kind: "answer"; response: { answer: string } }
  | { kind: "error" };

function truncate(content: string): string {
  return content.length > PER_TURN_CHAR_CAP ? content.slice(0, PER_TURN_CHAR_CAP) : content;
}

export function buildHistory(messages: readonly HistoryMessage[]): ChatTurn[] {
  // Pair each user question with the answer that immediately follows it; a
  // question followed by an error (or nothing) yields no pair, which keeps the
  // sequence strictly alternating.
  const pairs: [ChatTurn, ChatTurn][] = [];
  for (let i = 0; i < messages.length - 1; i++) {
    const question = messages[i];
    const reply = messages[i + 1];
    if (question.kind === "user" && reply.kind === "answer") {
      const userContent = truncate(question.text);
      const assistantContent = truncate(reply.response.answer);
      // Drop a degenerate exchange: the API's Turn.content requires min_length=1,
      // and an empty/whitespace-only turn carries no useful context anyway.
      if (!userContent.trim() || !assistantContent.trim()) continue;
      pairs.push([
        { role: "user", content: userContent },
        { role: "assistant", content: assistantContent },
      ]);
    }
  }

  // Keep the most recent whole exchanges within both budgets (newest first).
  const selected: ChatTurn[] = [];
  let totalChars = 0;
  for (let i = pairs.length - 1; i >= 0; i--) {
    const [userTurn, assistantTurn] = pairs[i];
    const pairChars = userTurn.content.length + assistantTurn.content.length;
    if (selected.length + 2 > MAX_HISTORY_TURNS) break;
    if (totalChars + pairChars > TOTAL_HISTORY_CHAR_BUDGET) break;
    selected.unshift(userTurn, assistantTurn);
    totalChars += pairChars;
  }
  return selected;
}
