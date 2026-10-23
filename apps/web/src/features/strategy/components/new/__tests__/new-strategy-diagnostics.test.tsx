// screen-07 "04 진단" 구획 재도입 회귀 테스트 — 지원 함수 사전(backed)·저장된 초안·파일/예제 버튼.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PINE_FUNCTION_LEXICON } from "@/features/strategy/pine-lexicon";
import type { WizardDraft } from "@/features/strategy/draft";

// 제어 가능한 draft 스냅샷 — 빈 상태 vs present 상태 분기 검증용.
const hoisted = vi.hoisted(() => ({
  draftSnapshot: { value: null as WizardDraft | null },
  saveWizardDraft: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Monaco 에디터는 무겁고 브라우저 API 를 요구하므로 textarea 로 대체.
vi.mock("@/components/monaco/pine-editor", () => ({
  PineEditor: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea data-testid="pine-editor" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

// 파싱 결과 패널은 이 테스트 범위 밖 — 스텁으로 대체.
vi.mock("@/features/strategy/components/new/parse-result-panel", () => ({
  ParseResultPanel: () => <div data-testid="parse-result-panel" />,
}));

vi.mock("@/features/strategy/hooks", () => ({
  // [ADR-041] 위저드가 AI 생성 카드를 품는다. 이 파일들은 **위저드**를 재는 곳이라
  // 생성 본문은 대상이 아니다 — 결과 없음 상태로 고정한다.
  // 생성 계약은 `generate-with-ai.test.tsx` 가 잰다.
  useGenerateStrategy: () => ({
    mutate: () => {},
    data: undefined,
    isPending: false,
    isError: false,
  }),
  useCreateStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useCurrentSourceParse: () => ({ parse: vi.fn(), result: null, loading: false, error: null }),
}));

vi.mock("@/features/strategy/draft", () => ({
  useDraftSnapshot: () => hoisted.draftSnapshot.value,
  useAutoSaveDraft: () => undefined,
  clearOtherUsersDrafts: vi.fn(),
  clearWizardDraft: vi.fn(),
  saveWizardDraft: hoisted.saveWizardDraft,
}));

import { NewStrategyWizard } from "@/features/strategy/components/new/new-strategy-wizard";

function renderWizard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NewStrategyWizard />
    </QueryClientProvider>,
  );
}

describe("NewStrategyWizard — 04 진단 구획", () => {
  afterEach(() => {
    cleanup();
    hoisted.draftSnapshot.value = null;
    hoisted.saveWizardDraft.mockReset();
  });

  it("선택형 AI는 처음 펼칠 때 마운트하고 다시 접어도 작성한 요청을 보존한다", async () => {
    const { container } = renderWizard();
    const details = container.querySelector<HTMLDetailsElement>("details.create-ai-tools")!;
    expect(screen.queryByLabelText("어떤 전략을 원하시나요?")).not.toBeInTheDocument();
    details.open = true;
    fireEvent(details, new Event("toggle"));
    const prompt = await screen.findByLabelText("어떤 전략을 원하시나요?");
    fireEvent.change(prompt, { target: { value: "이동평균 상향 돌파 시 진입" } });
    details.open = false;
    fireEvent(details, new Event("toggle"));
    details.open = true;
    fireEvent(details, new Event("toggle"));
    expect(screen.getByLabelText("어떤 전략을 원하시나요?")).toHaveValue(
      "이동평균 상향 돌파 시 진입",
    );
  });

  it("진단 섹션은 .diag-2 안에 지원 함수 사전·저장된 초안 두 .diag 카드를 그린다", () => {
    renderWizard();
    const section = screen.getByLabelText("진단");
    const grid = section.querySelector(".diag-2");
    expect(grid).toBeTruthy();
    expect(grid!.querySelectorAll(".card.diag")).toHaveLength(2);
    expect(within(section).getByLabelText("지원 함수 사전")).toBeTruthy();
    expect(within(section).getByLabelText("저장된 초안")).toBeTruthy();
    expect(within(section).getByRole("heading", { name: "지원 함수와 저장된 초안" })).toBeVisible();
    expect(within(section).getByText(/지원 함수의 의미를 찾아보고/)).toHaveTextContent(
      "이 브라우저에 저장된 초안을 이어서 작성",
    );
  });

  it("원문과 판정 영역을 native 링크로 왕복하고 편집기 Tab 이동 방법을 확인할 수 있다", () => {
    renderWizard();
    fireEvent.change(screen.getByTestId("pine-editor"), {
      target: { value: "strategy('navigation')" },
    });
    const source = screen.getByLabelText("Pine 소스");
    const result = screen.getByLabelText("파싱 결과");
    expect(source).toHaveAttribute("id", "strategy-pine-source");
    expect(source).toHaveAttribute("tabindex", "-1");
    expect(result).toHaveAttribute("id", "strategy-parse-result");
    expect(result).toHaveAttribute("tabindex", "-1");
    expect(within(source).getByRole("link", { name: "판정 결과 보기" })).toHaveAttribute(
      "href",
      "#strategy-parse-result",
    );
    expect(within(result).getByRole("link", { name: "원문 다시 보기" })).toHaveAttribute(
      "href",
      "#strategy-pine-source",
    );
    expect(
      within(source).getByText(
        "키보드로 나가기: Mac Ctrl+Shift+M / Windows·Linux Ctrl+M 후 Tab을 누르세요.",
      ),
    ).toBeVisible();
  });

  it("지원 함수 사전은 pine-lexicon 전체 항목을 .lexicon-list 로 렌더한다 (backed)", () => {
    renderWizard();
    const list = screen.getByTestId("lexicon-list");
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(Object.keys(PINE_FUNCTION_LEXICON).length);
    // 첫 항목은 삽입 순서상 ta.sma — 원시 enum 이 아니라 코드 심볼이라 그대로 노출.
    expect(within(items[0]!).getByText("ta.sma")).toBeTruthy();
  });

  it("저장된 초안이 없으면 빈 상태 + '현재 입력을 초안으로 저장' CTA 를 그린다", () => {
    hoisted.draftSnapshot.value = null;
    renderWizard();
    expect(screen.getByTestId("draft-empty")).toBeTruthy();
    expect(screen.getByText("저장된 초안이 없습니다.")).toBeTruthy();
    fireEvent.click(screen.getByText("현재 입력을 초안으로 저장"));
    expect(hoisted.saveWizardDraft).toHaveBeenCalledTimes(1);
  });

  it("저장된 초안이 있으면 present 상태 + '이어서 작성' 을 그린다", () => {
    hoisted.draftSnapshot.value = {
      version: 1,
      savedAt: Date.now(),
      method: "direct",
      pineSource: "//@version=5",
      metadata: { name: "저장된 것" },
    };
    renderWizard();
    const present = screen.getByTestId("draft-present");
    // 초안 present 시 복원 Dialog 도 열려 "이어서 작성" 이 2곳(카드+다이얼로그)이므로 카드 내부로 좁힌다.
    expect(within(present).getByText("이어서 작성")).toBeTruthy();
    expect(within(present).getByText(/저장한 초안이 있습니다/)).toBeTruthy();
    expect(screen.queryByTestId("draft-empty")).toBeNull();
  });

  it("Pine 소스 툴바에 파일 열기·예제로 원문 바꾸기 버튼이 있다", () => {
    renderWizard();
    expect(screen.getByText("파일 열기")).toBeTruthy();
    expect(screen.getByText("예제로 원문 바꾸기")).toBeTruthy();
    expect(screen.getByTestId("pine-file-input")).toBeTruthy();
  });
});
