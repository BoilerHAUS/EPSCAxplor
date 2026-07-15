import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth";
import { apiClient } from "./api-client";
import type { TokenResponse } from "./types";

vi.mock("./api-client", () => {
  class ApiError extends Error {
    constructor(
      public readonly status: number,
      public readonly detail: string,
    ) {
      super(`${status}: ${detail}`);
    }
  }
  return {
    ApiError,
    apiClient: {
      login: vi.fn(),
      refresh: vi.fn(),
      logout: vi.fn(),
      getAccessToken: vi.fn(),
      setAccessToken: vi.fn(),
    },
  };
});

const mocked = vi.mocked(apiClient);

function tokens(expiresIn: number): TokenResponse {
  return { access_token: "jwt", token_type: "bearer", expires_in: expiresIn };
}

let latest: ReturnType<typeof useAuth>;

function Probe() {
  latest = useAuth();
  return <span data-testid="status">{latest.status}</span>;
}

function renderAuth() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("re-hydrates via silent refresh on mount", async () => {
    mocked.refresh.mockResolvedValueOnce(tokens(900));

    renderAuth();
    expect(screen.getByTestId("status").textContent).toBe("loading");

    await flush();

    expect(mocked.refresh).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("status").textContent).toBe("authenticated");
  });

  it("becomes unauthenticated when the silent refresh fails", async () => {
    mocked.refresh.mockRejectedValueOnce(new Error("401"));

    renderAuth();
    await flush();

    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
  });

  it("login authenticates and schedules a refresh before the token expires", async () => {
    mocked.refresh.mockRejectedValueOnce(new Error("401"));
    mocked.login.mockResolvedValueOnce(tokens(900));

    renderAuth();
    await flush();

    await act(async () => {
      await latest.login("user@example.com", "hunter22");
    });
    expect(screen.getByTestId("status").textContent).toBe("authenticated");
    expect(mocked.login).toHaveBeenCalledWith("user@example.com", "hunter22");

    // scheduled silent refresh fires before the 900s expiry
    mocked.refresh.mockResolvedValueOnce(tokens(900));
    await act(async () => {
      vi.advanceTimersByTime(900 * 1000);
    });
    expect(mocked.refresh).toHaveBeenCalledTimes(2);
  });

  it("propagates login failures and stays unauthenticated", async () => {
    mocked.refresh.mockRejectedValueOnce(new Error("401"));
    mocked.login.mockRejectedValueOnce(new Error("unauthorized"));

    renderAuth();
    await flush();

    await expect(
      act(async () => {
        await latest.login("user@example.com", "wrong");
      }),
    ).rejects.toThrow("unauthorized");
    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
  });

  it("logout clears state and cancels the scheduled refresh", async () => {
    mocked.refresh.mockResolvedValueOnce(tokens(900));
    mocked.logout.mockResolvedValueOnce(undefined);

    renderAuth();
    await flush();
    expect(screen.getByTestId("status").textContent).toBe("authenticated");

    await act(async () => {
      await latest.logout();
    });

    expect(mocked.logout).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");

    // no further silent refresh after logout
    await act(async () => {
      vi.advanceTimersByTime(3600 * 1000);
    });
    expect(mocked.refresh).toHaveBeenCalledTimes(1);
  });

  it("marks the session unauthenticated when a scheduled refresh fails", async () => {
    mocked.refresh.mockResolvedValueOnce(tokens(900)).mockRejectedValueOnce(new Error("401"));

    renderAuth();
    await flush();
    expect(screen.getByTestId("status").textContent).toBe("authenticated");

    await act(async () => {
      vi.advanceTimersByTime(900 * 1000);
    });

    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
  });

  it("does not reschedule or set state when a refresh is in flight at unmount", async () => {
    let resolveRefresh!: (t: TokenResponse) => void;
    mocked.refresh
      .mockResolvedValueOnce(tokens(900))
      .mockImplementationOnce(() => new Promise((resolve) => (resolveRefresh = resolve)));

    const { unmount } = renderAuth();
    await flush();
    expect(screen.getByTestId("status").textContent).toBe("authenticated");

    // fire the scheduled refresh; it stays in flight
    await act(async () => {
      vi.advanceTimersByTime(900 * 1000);
    });
    expect(mocked.refresh).toHaveBeenCalledTimes(2);

    unmount();
    await act(async () => {
      resolveRefresh(tokens(900));
      await Promise.resolve();
    });

    // the resolved in-flight refresh must not schedule an orphaned timer
    await act(async () => {
      vi.advanceTimersByTime(3600 * 1000);
    });
    expect(mocked.refresh).toHaveBeenCalledTimes(2);
  });

  it("useAuth throws when used outside the provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/AuthProvider/);
    spy.mockRestore();
  });
});
