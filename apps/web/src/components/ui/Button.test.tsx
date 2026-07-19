import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

afterEach(cleanup);

describe("Button", () => {
  it("renders its label and fires onClick", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Sign in</Button>);

    const button = screen.getByRole("button", { name: "Sign in" });
    fireEvent.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(button).toHaveProperty("type", "button");
  });

  it("supports submit type", () => {
    render(<Button type="submit">Sign in</Button>);
    expect(screen.getByRole("button")).toHaveProperty("type", "submit");
  });

  it("does not fire onClick when disabled", () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Sign in
      </Button>,
    );

    const button = screen.getByRole("button");
    fireEvent.click(button);

    expect(onClick).not.toHaveBeenCalled();
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it.each(["primary", "secondary", "ghost", "danger"] as const)(
    "maps the %s variant to a class",
    (variant) => {
      render(<Button variant={variant}>Label</Button>);
      const button = screen.getByRole("button");
      expect(button.textContent).toBe("Label");
      expect(button.className).toContain(`btn--${variant}`);
    },
  );

  it.each(["sm", "md", "lg"] as const)("maps the %s size to a class", (size) => {
    render(<Button size={size}>Label</Button>);
    const button = screen.getByRole("button");
    expect(button.textContent).toBe("Label");
    expect(button.className).toContain(`btn--${size}`);
  });

  it("keeps hover and focus in CSS — no inline style mutation", () => {
    render(<Button>Label</Button>);
    const button = screen.getByRole("button");

    fireEvent.mouseEnter(button);
    fireEvent.focus(button);

    // hover (:hover) and focus (:focus-visible) are CSS-driven now; the
    // component sets no inline background or box-shadow on these events
    expect(button.className).toContain("btn");
    expect(button.style.background).toBe("");
    expect(button.style.boxShadow).toBe("");
  });
});
