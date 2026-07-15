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
    "renders the %s variant",
    (variant) => {
      render(<Button variant={variant}>Label</Button>);
      expect(screen.getByRole("button").textContent).toBe("Label");
    },
  );

  it.each(["sm", "md", "lg"] as const)("renders the %s size", (size) => {
    render(<Button size={size}>Label</Button>);
    expect(screen.getByRole("button").textContent).toBe("Label");
  });

  it("applies hover styling on mouse enter and clears it on leave", () => {
    render(<Button variant="secondary">Label</Button>);
    const button = screen.getByRole("button");

    fireEvent.mouseEnter(button);
    expect(button.style.background).toBe("var(--surface-hover)");

    fireEvent.mouseLeave(button);
    expect(button.style.background).toBe("var(--surface-card)");
  });

  it("shows the amber focus ring on focus and removes it on blur", () => {
    render(<Button>Label</Button>);
    const button = screen.getByRole("button");

    fireEvent.focus(button);
    expect(button.style.boxShadow).toBe("var(--shadow-focus)");

    fireEvent.blur(button);
    expect(button.style.boxShadow).toBe("none");
  });
});
