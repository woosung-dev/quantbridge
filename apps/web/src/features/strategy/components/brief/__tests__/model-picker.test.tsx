// provider 모델 카탈로그 선택 UI.
//
// 이 파일이 잠그는 것 넷.
//  ⑴ 설정된 모델이 provider 목록에 **없으면** 말한다 — 2026-08-28 `gemini-2.0-flash` 폐기(404) 사건.
//  ⑵ ★`configured_listed` 는 **3값**이다. `null`(목록을 못 읽음)에 경고를 띄우면 멀쩡한 설정이 빨갛게 보인다.
//  ⑶ 고르면 provider 와 model 을 **함께** 올린다 — 서버가 한쪽만 오면 422 로 거절한다.
//  ⑷ 목록을 못 읽어도 UI 를 **없애지 않는다**(비활성 + 사유). 없애면 왜 사라졌는지 알 수 없다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ModelPicker } from "@/features/strategy/components/brief/model-picker";

const mockUseLlmModels = vi.hoisted(() => vi.fn());
vi.mock("@/features/strategy/hooks", () => ({
  useLlmModels: (...args: unknown[]) => mockUseLlmModels(...args),
}));

function provider(over: Record<string, unknown> = {}) {
  return {
    provider: "gemini",
    models: [
      { id: "gemini-3.5-flash-lite", display_name: "Gemini 3.5 Flash Lite" },
      { id: "gemini-3.6-flash", display_name: "Gemini 3.6 Flash" },
    ],
    total_seen: 53,
    configured: "gemini-3.5-flash-lite",
    configured_listed: true,
    error: null,
    ...over,
  };
}

function ready(providers: unknown[], active = "openai") {
  mockUseLlmModels.mockReturnValue({
    isPending: false,
    isError: false,
    data: { providers, order: ["openai", "gemini"], active },
  });
}

describe("ModelPicker", () => {
  afterEach(() => {
    cleanup();
    mockUseLlmModels.mockReset();
  });

  it("설정된 모델이 목록에 없으면 말한다", () => {
    ready([provider({ configured: "gemini-2.0-flash", configured_listed: false })]);
    render(<ModelPicker enabled value={null} onChange={vi.fn()} />);
    const drift = screen.getByTestId("model-picker-drift");
    expect(drift.textContent).toContain("gemini-2.0-flash");
  });

  it("목록을 못 읽어 모르는 상태(null)에서는 경고하지 않는다", () => {
    // ★이것이 없으면 `configured_listed` 를 2값으로 접어도 위 테스트가 통과한다.
    ready([provider({ configured_listed: null, error: "AuthenticationError", models: [] })]);
    render(<ModelPicker enabled value={null} onChange={vi.fn()} />);
    expect(screen.queryByTestId("model-picker-drift")).toBeNull();
  });

  it("목록에 있는 상태(true)에서도 경고하지 않는다", () => {
    ready([provider()]);
    render(<ModelPicker enabled value={null} onChange={vi.fn()} />);
    expect(screen.queryByTestId("model-picker-drift")).toBeNull();
  });

  it("고르면 provider 와 model 을 함께 올린다", () => {
    ready([provider()]);
    const onChange = vi.fn();
    render(<ModelPicker enabled value={null} onChange={onChange} />);
    fireEvent.change(screen.getByTestId("model-picker-select"), {
      target: { value: "gemini gemini-3.6-flash" },
    });
    expect(onChange).toHaveBeenCalledWith({ provider: "gemini", model: "gemini-3.6-flash" });
  });

  it("기본 설정으로 되돌리면 null 을 올린다", () => {
    ready([provider()]);
    const onChange = vi.fn();
    render(
      <ModelPicker
        enabled
        value={{ provider: "gemini", model: "gemini-3.6-flash" }}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByTestId("model-picker-select"), {
      target: { value: "__default__" },
    });
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("목록 조회가 실패해도 UI 는 남고 사유를 적는다", () => {
    mockUseLlmModels.mockReturnValue({ isPending: false, isError: true, data: undefined });
    render(<ModelPicker enabled value={null} onChange={vi.fn()} />);
    expect(screen.getByTestId("model-picker-error")).toBeTruthy();
    expect(screen.getByTestId("model-picker-select").hasAttribute("disabled")).toBe(true);
  });

  it("모델이 0건인 provider 는 그룹을 만들지 않는다", () => {
    ready([provider({ models: [], configured_listed: null, error: "키가 설정되지 않았습니다" })]);
    render(<ModelPicker enabled value={null} onChange={vi.fn()} />);
    // 기본 설정 항목 하나만 남는다.
    expect(screen.getAllByRole("option")).toHaveLength(1);
  });

  it("접혀 있으면(enabled=false) 목록을 부르지 않는다", () => {
    mockUseLlmModels.mockReturnValue({ isPending: true, isError: false, data: undefined });
    render(<ModelPicker enabled={false} value={null} onChange={vi.fn()} />);
    expect(mockUseLlmModels).toHaveBeenCalledWith(false);
  });
});
