import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Input } from "./Input";

afterEach(cleanup);

describe("Input", () => {
  it("emits the raw string value on change", () => {
    const onChange = vi.fn();
    render(<Input ariaLabel="Email" value="" onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });

    expect(onChange).toHaveBeenCalledWith("user@example.com");
  });

  it("tolerates a missing onChange handler", () => {
    render(<Input ariaLabel="Email" />);
    expect(() =>
      fireEvent.change(screen.getByLabelText("Email"), { target: { value: "x" } }),
    ).not.toThrow();
  });

  it("passes through form attributes", () => {
    render(
      <Input
        ariaLabel="Password"
        type="password"
        name="password"
        autoComplete="current-password"
        required
        placeholder="Password"
      />,
    );

    const input = screen.getByLabelText("Password") as HTMLInputElement;
    expect(input.type).toBe("password");
    expect(input.name).toBe("password");
    expect(input.autocomplete).toBe("current-password");
    expect(input.required).toBe(true);
    expect(input.placeholder).toBe("Password");
  });

  it("renders the error message with a red border", () => {
    render(<Input ariaLabel="Password" error="Invalid email or password." />);

    expect(screen.getByRole("alert").textContent).toBe("Invalid email or password.");
    const input = screen.getByLabelText("Password");
    expect(input.style.border).toContain("var(--status-error)");
    expect(input.getAttribute("aria-invalid")).toBe("true");
  });

  it("relies on :focus-visible instead of inline focus styles", () => {
    render(<Input ariaLabel="Email" />);
    const input = screen.getByLabelText("Email");

    fireEvent.focus(input);
    // focus is handled by the global :focus-visible ring, not JS — the
    // element gets no inline focus shadow, and the border is unchanged
    expect(input.style.boxShadow).toBe("");
    expect(input.style.border).toContain("var(--border-default)");

    fireEvent.blur(input);
    expect(input.style.boxShadow).toBe("");
  });

  it("supports the small size and disabled state", () => {
    render(<Input ariaLabel="Email" size="sm" disabled />);
    const input = screen.getByLabelText("Email") as HTMLInputElement;
    expect(input.disabled).toBe(true);
    expect(input.style.padding).toBe("6px 10px");
  });
});
