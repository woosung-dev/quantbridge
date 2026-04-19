import { describe, expect, it } from "vitest";
import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { TagInput, type TagInputProps } from "../tag-input";

function Harness(props: Omit<TagInputProps, "value" | "onChange"> & { initial?: string[] }) {
  const { initial = [], ...rest } = props;
  const [value, setValue] = useState<string[]>(initial);
  return (
    <>
      <TagInput {...rest} value={value} onChange={setValue} />
      <pre data-testid="value">{JSON.stringify(value)}</pre>
    </>
  );
}

function getInput(): HTMLInputElement {
  const group = screen.getByRole("group", { name: "태그" });
  const input = group.querySelector("input");
  if (!input) throw new Error("input not found");
  return input as HTMLInputElement;
}

function readValue(): string[] {
  return JSON.parse(screen.getByTestId("value").textContent ?? "[]") as string[];
}

describe("TagInput", () => {
  it("Enter → trimmed chip 추가 + input clear", () => {
    render(<Harness />);
    const input = getInput();
    fireEvent.change(input, { target: { value: "  trend  " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(readValue()).toEqual(["trend"]);
    expect(input.value).toBe("");
  });

  it("comma key → chip 추가", () => {
    render(<Harness />);
    const input = getInput();
    fireEvent.change(input, { target: { value: "ema" } });
    fireEvent.keyDown(input, { key: "," });
    expect(readValue()).toEqual(["ema"]);
    expect(input.value).toBe("");
  });

  it("Tab key (non-empty draft) → chip 추가", () => {
    render(<Harness />);
    const input = getInput();
    fireEvent.change(input, { target: { value: "crossover" } });
    fireEvent.keyDown(input, { key: "Tab" });
    expect(readValue()).toEqual(["crossover"]);
    expect(input.value).toBe("");
  });

  it("빈 input Backspace → 마지막 chip 제거", () => {
    render(<Harness initial={["alpha", "beta"]} />);
    const input = getInput();
    fireEvent.keyDown(input, { key: "Backspace" });
    expect(readValue()).toEqual(["alpha"]);
  });

  it("중복 태그는 추가되지 않음", () => {
    render(<Harness initial={["trend"]} />);
    const input = getInput();
    fireEvent.change(input, { target: { value: "trend" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(readValue()).toEqual(["trend"]);
  });

  it("maxTags 도달 시 Enter 추가 차단", () => {
    render(<Harness initial={["a", "b", "c", "d", "e"]} maxTags={5} />);
    const input = getInput();
    fireEvent.change(input, { target: { value: "f" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(readValue()).toEqual(["a", "b", "c", "d", "e"]);
    expect(input.value).toBe("f");
  });

  it("chip × 버튼 클릭 → 해당 태그 제거", () => {
    render(<Harness initial={["alpha", "beta", "gamma"]} />);
    fireEvent.click(screen.getByRole("button", { name: "beta 태그 제거" }));
    expect(readValue()).toEqual(["alpha", "gamma"]);
  });

  it("빈 input 에서 Enter 는 아무 동작 없음", () => {
    render(<Harness initial={["x"]} />);
    const input = getInput();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(readValue()).toEqual(["x"]);
  });
});
