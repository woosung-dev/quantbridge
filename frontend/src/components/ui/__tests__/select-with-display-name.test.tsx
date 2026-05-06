// Sprint 33 BL-176 hotfix 회귀 (dogfood Day 6 발견):
// SelectWithDisplayName.handleValueChange 가 v=null (base-ui transient state) 시
// callback skip — form 의 zod UUID schema 가 "" reject 하여 ZodError raise 차단.

import { fireEvent, render, screen } from "@testing-library/react";
import * as React from "react";
import { vi } from "vitest";

// base-ui Select mock — Worker B live-session-form.test pattern 복제 + null trigger button 추가.
vi.mock("@/components/ui/select", () => {
  type SelectProps = {
    value: string;
    onValueChange?: (v: string | null) => void;
    children: React.ReactNode;
  };
  const Ctx = React.createContext<{
    value: string;
    onValueChange?: (v: string | null) => void;
  } | null>(null);

  const Select = ({ value, onValueChange, children }: SelectProps) => (
    <div data-testid="mock-select">
      <Ctx.Provider value={{ value, onValueChange }}>{children}</Ctx.Provider>
      {/* test hook — null transient state 직접 트리거. */}
      <button
        data-testid="mock-trigger-null"
        onClick={() => onValueChange?.(null)}
      >
        null
      </button>
      <button
        data-testid="mock-trigger-uuid"
        onClick={() =>
          onValueChange?.("019a1234-5678-7000-a000-0123456789ab")
        }
      >
        uuid
      </button>
    </div>
  );

  const SelectTrigger = ({
    children,
    "data-testid": testId,
  }: {
    children: React.ReactNode;
    "data-testid"?: string;
  }) => <div data-testid={testId}>{children}</div>;

  const SelectValue = ({
    children,
    placeholder,
  }: {
    children?: ((v: string | null) => React.ReactNode) | React.ReactNode;
    placeholder?: string;
  }) => {
    const ctx = React.useContext(Ctx);
    if (typeof children === "function") {
      return <>{(children as (v: string | null) => React.ReactNode)(ctx?.value || null)}</>;
    }
    return <>{children ?? placeholder}</>;
  };

  const SelectContent = ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  );

  const SelectItem = ({
    value,
    children,
  }: {
    value: string;
    children: React.ReactNode;
  }) => <button data-value={value}>{children}</button>;

  return { Select, SelectTrigger, SelectValue, SelectContent, SelectItem };
});

import { SelectWithDisplayName } from "../select-with-display-name";

describe("SelectWithDisplayName.handleValueChange (BL-176 hotfix)", () => {
  const OPTIONS = [
    { value: "019a1234-5678-7000-a000-0123456789ab", label: "Strategy A" },
  ];

  it("skips onValueChange when v=null (base-ui transient state)", () => {
    const spy = vi.fn();
    render(
      <SelectWithDisplayName
        options={OPTIONS}
        value=""
        onValueChange={spy}
        placeholder="선택"
      />,
    );
    fireEvent.click(screen.getByTestId("mock-trigger-null"));
    // null 시 callback skip — form prior value 보존, ZodError 미발생.
    expect(spy).not.toHaveBeenCalled();
  });

  it("forwards UUID string when v is valid", () => {
    const spy = vi.fn();
    render(
      <SelectWithDisplayName
        options={OPTIONS}
        value=""
        onValueChange={spy}
        placeholder="선택"
      />,
    );
    fireEvent.click(screen.getByTestId("mock-trigger-uuid"));
    expect(spy).toHaveBeenCalledWith("019a1234-5678-7000-a000-0123456789ab");
    expect(spy).toHaveBeenCalledTimes(1);
  });

  // BL-164 base behavior (label 표시 + UUID 미노출) 회귀는 worker B 의
  // live-session-form.test.tsx 5 case 에서 이미 검증. 본 spec 은 hotfix 만 cover.
});

describe("SelectWithDisplayName clear button (BL-176)", () => {
  const OPTIONS = [
    { value: "019a1234-5678-7000-a000-0123456789ab", label: "Strategy A" },
  ];

  it("clear 버튼을 onClear+value 있을 때만 렌더한다", () => {
    const spy = vi.fn();
    const { rerender } = render(
      <SelectWithDisplayName
        options={OPTIONS}
        value="019a1234-5678-7000-a000-0123456789ab"
        onValueChange={vi.fn()}
        placeholder="선택"
        onClear={spy}
        triggerTestId="t"
      />,
    );
    expect(screen.getByTestId("t-clear")).toBeInTheDocument();

    // value 없으면 clear 버튼 사라짐
    rerender(
      <SelectWithDisplayName
        options={OPTIONS}
        value=""
        onValueChange={vi.fn()}
        placeholder="선택"
        onClear={spy}
        triggerTestId="t"
      />,
    );
    expect(screen.queryByTestId("t-clear")).not.toBeInTheDocument();
  });

  it("onClear 미전달 시 clear 버튼 렌더하지 않는다", () => {
    render(
      <SelectWithDisplayName
        options={OPTIONS}
        value="019a1234-5678-7000-a000-0123456789ab"
        onValueChange={vi.fn()}
        placeholder="선택"
        triggerTestId="t2"
      />,
    );
    expect(screen.queryByTestId("t2-clear")).not.toBeInTheDocument();
  });

  it("clear 버튼 클릭 시 onClear 호출, onValueChange 미호출", () => {
    const onClear = vi.fn();
    const onValueChange = vi.fn();
    render(
      <SelectWithDisplayName
        options={OPTIONS}
        value="019a1234-5678-7000-a000-0123456789ab"
        onValueChange={onValueChange}
        placeholder="선택"
        onClear={onClear}
        triggerTestId="t3"
      />,
    );
    fireEvent.click(screen.getByTestId("t3-clear"));
    expect(onClear).toHaveBeenCalledTimes(1);
    expect(onValueChange).not.toHaveBeenCalled();
  });
});
