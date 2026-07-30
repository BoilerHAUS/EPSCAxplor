import { describe, expect, it } from "vitest";
import {
  buildHistory,
  type HistoryMessage,
  MAX_HISTORY_TURNS,
  PER_TURN_CHAR_CAP,
  TOTAL_HISTORY_CHAR_BUDGET,
} from "./chatHistory";

const user = (text: string): HistoryMessage => ({ kind: "user", text });
const answer = (a: string): HistoryMessage => ({ kind: "answer", response: { answer: a } });
const errored = (): HistoryMessage => ({ kind: "error" });

describe("buildHistory", () => {
  it("returns an empty history when there are no messages", () => {
    expect(buildHistory([])).toEqual([]);
  });

  it("maps completed exchanges to alternating user/assistant turns", () => {
    const history = buildHistory([user("q1"), answer("a1"), user("q2"), answer("a2")]);
    expect(history).toEqual([
      { role: "user", content: "q1" },
      { role: "assistant", content: "a1" },
      { role: "user", content: "q2" },
      { role: "assistant", content: "a2" },
    ]);
  });

  it("excludes a question whose turn errored (keeps history alternating)", () => {
    const history = buildHistory([user("q1"), answer("a1"), user("q2"), errored()]);
    expect(history).toEqual([
      { role: "user", content: "q1" },
      { role: "assistant", content: "a1" },
    ]);
  });

  it("skips an exchange with empty answer content (API requires non-empty turns)", () => {
    const history = buildHistory([user("q1"), answer(""), user("q2"), answer("a2")]);
    expect(history).toEqual([
      { role: "user", content: "q2" },
      { role: "assistant", content: "a2" },
    ]);
  });

  it("skips an exchange whose answer is whitespace-only", () => {
    expect(buildHistory([user("q1"), answer("   ")])).toEqual([]);
  });

  it("drops a trailing unanswered question", () => {
    const history = buildHistory([user("q1"), answer("a1"), user("q2")]);
    expect(history).toEqual([
      { role: "user", content: "q1" },
      { role: "assistant", content: "a1" },
    ]);
  });

  it("keeps only the most recent MAX_HISTORY_TURNS turns", () => {
    const msgs: HistoryMessage[] = [];
    for (let n = 0; n < 5; n++) {
      msgs.push(user(`q${n}`), answer(`a${n}`));
    }
    const history = buildHistory(msgs); // 10 turns available

    expect(history).toHaveLength(MAX_HISTORY_TURNS);
    // Valid API shape: user-first, assistant-last, alternating.
    expect(history[0].role).toBe("user");
    expect(history[history.length - 1].role).toBe("assistant");
    // The most recent exchange is retained.
    expect(history[history.length - 1].content).toBe("a4");
  });

  it("truncates over-long turn content to the per-turn cap", () => {
    const long = "x".repeat(PER_TURN_CHAR_CAP + 500);
    const history = buildHistory([user("q1"), answer(long)]);
    expect(history[1].content).toHaveLength(PER_TURN_CHAR_CAP);
  });

  it("stays within the total char budget by dropping oldest whole exchanges", () => {
    const big = "y".repeat(PER_TURN_CHAR_CAP); // 4000; a pair is 8000
    const msgs: HistoryMessage[] = [];
    for (let n = 0; n < 4; n++) {
      msgs.push(user(big), answer(big));
    }
    const history = buildHistory(msgs);

    const total = history.reduce((sum, turn) => sum + turn.content.length, 0);
    expect(total).toBeLessThanOrEqual(TOTAL_HISTORY_CHAR_BUDGET);
    expect(history.length % 2).toBe(0); // whole exchanges only
    expect(history[0].role).toBe("user");
  });
});
