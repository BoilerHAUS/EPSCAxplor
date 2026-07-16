import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppHeader } from "./AppHeader";

const { mockLogout, mockUsePathname } = vi.hoisted(() => ({
  mockLogout: vi.fn(),
  mockUsePathname: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: mockUsePathname,
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", login: vi.fn(), logout: mockLogout }),
}));

describe("AppHeader", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/chat");
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("links to chat, documents, and history", () => {
    render(<AppHeader />);
    expect((screen.getByRole("link", { name: "Chat" }) as HTMLAnchorElement).href).toContain(
      "/chat",
    );
    expect(
      (screen.getByRole("link", { name: "Documents" }) as HTMLAnchorElement).href,
    ).toContain("/documents");
    expect(
      (screen.getByRole("link", { name: "History" }) as HTMLAnchorElement).href,
    ).toContain("/history");
  });

  it("marks the active route", () => {
    mockUsePathname.mockReturnValue("/documents");
    render(<AppHeader />);
    expect(screen.getByRole("link", { name: "Documents" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: "Chat" }).getAttribute("aria-current")).toBeNull();
  });

  it("signs out", () => {
    render(<AppHeader />);
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(mockLogout).toHaveBeenCalled();
  });
});
