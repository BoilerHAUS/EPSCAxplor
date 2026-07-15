import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryInput } from "./QueryInput";

afterEach(cleanup);

const UNIONS = ["IBEW", "Ironworkers"];

function textarea(): HTMLTextAreaElement {
  return screen.getByRole("textbox") as HTMLTextAreaElement;
}

describe("QueryInput", () => {
  it("submits the trimmed query and clears the input", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} unions={UNIONS} />);

    fireEvent.change(textarea(), { target: { value: "  What is the overtime rate?  " } });
    fireEvent.click(screen.getByLabelText("Send"));

    expect(onSubmit).toHaveBeenCalledWith("What is the overtime rate?");
    expect(textarea().value).toBe("");
  });

  it("submits on Enter and inserts a newline on Shift+Enter", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} unions={UNIONS} />);

    fireEvent.change(textarea(), { target: { value: "What is the overtime rate?" } });
    fireEvent.keyDown(textarea(), { key: "Enter", shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.keyDown(textarea(), { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("What is the overtime rate?");
  });

  it("does not submit blank queries", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} unions={UNIONS} />);

    fireEvent.change(textarea(), { target: { value: "   " } });
    fireEvent.keyDown(textarea(), { key: "Enter" });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("does not submit while disabled", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} unions={UNIONS} disabled />);

    fireEvent.change(textarea(), { target: { value: "query" } });
    fireEvent.keyDown(textarea(), { key: "Enter" });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("prefixes the selected union so backend union detection picks it up", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} unions={UNIONS} />);

    fireEvent.change(screen.getByLabelText("Union filter"), { target: { value: "IBEW" } });
    fireEvent.change(textarea(), { target: { value: "What is the overtime rate?" } });
    fireEvent.keyDown(textarea(), { key: "Enter" });

    expect(onSubmit).toHaveBeenCalledWith("IBEW: What is the overtime rate?");
  });

  it("does not double-prefix when the query already names the union", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} unions={UNIONS} />);

    fireEvent.change(screen.getByLabelText("Union filter"), { target: { value: "IBEW" } });
    fireEvent.change(textarea(), { target: { value: "What is the ibew overtime rate?" } });
    fireEvent.keyDown(textarea(), { key: "Enter" });

    expect(onSubmit).toHaveBeenCalledWith("What is the ibew overtime rate?");
  });

  it("lists all unions plus an all-unions default", () => {
    render(<QueryInput onSubmit={vi.fn()} unions={UNIONS} />);

    const select = screen.getByLabelText("Union filter") as HTMLSelectElement;
    const labels = Array.from(select.options).map((o) => o.textContent);
    expect(labels).toContain("All unions");
    expect(labels).toContain("IBEW");
    expect(labels).toContain("Ironworkers");
  });

  it("hides the union filter when no unions are available", () => {
    render(<QueryInput onSubmit={vi.fn()} unions={[]} />);
    expect(screen.queryByLabelText("Union filter")).toBeNull();
  });
});
