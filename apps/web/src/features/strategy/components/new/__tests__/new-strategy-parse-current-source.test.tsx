import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { parseStrategy } from "@/features/strategy/api";
import { useCurrentSourceParse } from "@/features/strategy/hooks";
import { ParsePreviewResponseSchema, type ParsePreviewResponse } from "@/features/strategy/schemas";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
const editorHandle = vi.hoisted(() => ({
  revealLine1: vi.fn((_line: number) => true),
}));
vi.mock("@/components/monaco/pine-editor", async () => {
  const React = await import("react");
  type Handle = { revealLine1: (line: number) => boolean };
  type Props = { value: string; onChange: (value: string) => void };
  const PineEditorMock = React.forwardRef<Handle, Props>(function PineEditorMock(
    { value, onChange },
    ref,
  ) {
    React.useImperativeHandle(ref, () => editorHandle, []);
    return (
      <textarea
        data-testid="pine-editor"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  });
  return { PineEditor: PineEditorMock };
});
vi.mock("@/features/strategy/components/new/generate-with-ai", () => ({
  GenerateWithAI: () => null,
}));
vi.mock("@/features/strategy/components/new/parse-result-panel", () => ({
  ParseResultPanel: ({
    result,
    error,
    canSave,
    onRevealLine,
  }: {
    result: ParsePreviewResponse | null;
    error: string | null;
    canSave: boolean;
    onRevealLine?: (line: number) => void;
  }) => (
    <>
      <output data-testid="parse-status">{result?.status ?? "none"}</output>
      <output data-testid="parse-error">{error ?? ""}</output>
      {result?.errors.map((parseIssue) =>
        parseIssue.line !== null ? (
          <button
            key={`${parseIssue.code}-${parseIssue.line}`}
            type="button"
            onClick={() => onRevealLine?.(parseIssue.line!)}
          >
            {parseIssue.line}행으로 이동
          </button>
        ) : null,
      )}
      <button type="button" disabled={!canSave}>
        판정 저장
      </button>
    </>
  ),
}));
vi.mock("@/features/strategy/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/strategy/api")>()),
  parseStrategy: vi.fn(),
}));
import { NewStrategyWizard } from "@/features/strategy/components/new/new-strategy-wizard";

const parseMock = vi.mocked(parseStrategy);
const valid = ParsePreviewResponseSchema.parse({ status: "ok", pine_version: "v5" });
const invalid = ParsePreviewResponseSchema.parse({ status: "error", pine_version: "v5" });
let queryClient: QueryClient;
let originalScrollIntoView: PropertyDescriptor | undefined;
const scrollIntoView = vi.fn();

async function tick(ms = 1) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}
async function input(source: string) {
  fireEvent.change(screen.getByTestId("pine-editor"), { target: { value: source } });
  await tick(350);
  await tick();
}
function deferred() {
  let resolve!: (value: ParsePreviewResponse) => void;
  const promise = new Promise<ParsePreviewResponse>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
beforeEach(() => {
  vi.useFakeTimers();
  editorHandle.revealLine1.mockReset().mockReturnValue(true);
  scrollIntoView.mockReset();
  originalScrollIntoView = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: scrollIntoView,
  });
  parseMock.mockReset();
  localStorage.clear();
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
});
afterEach(() => {
  cleanup();
  if (originalScrollIntoView) {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", originalScrollIntoView);
  } else {
    Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  }
  queryClient.clear();
  vi.useRealTimers();
  localStorage.clear();
});
function renderWizard() {
  render(
    <QueryClientProvider client={queryClient}>
      <NewStrategyWizard />
    </QueryClientProvider>,
  );
  fireEvent.change(screen.getByLabelText("전략 이름"), { target: { value: "검증 전략" } });
}

describe("새 전략 — 현재 원문에 대한 파싱 판정", () => {
  it("leading blank line을 포함한 실제 요청 원문의 서버 행으로 이동한다", async () => {
    parseMock.mockImplementation(async (source) => {
      const line = source.split("\n").indexOf("bad token") + 1;
      return ParsePreviewResponseSchema.parse({
        status: "error",
        pine_version: "v5",
        errors: [{ code: "SYNTAX_ERROR", message: "bad token", line }],
      });
    });
    renderWizard();
    const source = "\n\nfirst line\nbad token";
    await input(source);

    expect(parseMock).toHaveBeenLastCalledWith(source, "test-token");
    fireEvent.click(screen.getByRole("button", { name: "4행으로 이동" }));
    expect(editorHandle.revealLine1).toHaveBeenCalledWith(4);
  });

  it("같은 trim 결과라도 공백 원문 변경은 이전 판정과 늦은 좌표를 무효화한다", async () => {
    const initial = deferred();
    const nextResult = ParsePreviewResponseSchema.parse({
      status: "error",
      pine_version: "v5",
      errors: [{ code: "SYNTAX_ERROR", message: "bad token", line: 3 }],
    });
    parseMock.mockImplementation((source) =>
      source === "bad token" ? initial.promise : Promise.resolve(nextResult),
    );
    renderWizard();
    fireEvent.change(screen.getByTestId("pine-editor"), { target: { value: "bad token" } });
    await tick(350);
    expect(parseMock).toHaveBeenLastCalledWith("bad token", "test-token");

    fireEvent.change(screen.getByTestId("pine-editor"), {
      target: { value: "\n\nbad token" },
    });
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "1행으로 이동" })).toBeNull();
    await tick(350);
    expect(parseMock).toHaveBeenLastCalledWith("\n\nbad token", "test-token");
    await tick();
    await act(async () => initial.resolve(valid));
    await tick();
    expect(screen.getByRole("button", { name: "3행으로 이동" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "1행으로 이동" })).toBeNull();
  });

  it("구조화된 서버 행으로 이동하고 editor에 맡긴다", async () => {
    const locatedError = ParsePreviewResponseSchema.parse({
      status: "error",
      pine_version: "v5",
      errors: [{ code: "SYNTAX_ERROR", message: "bad token", line: 7 }],
    });
    parseMock.mockResolvedValue(locatedError);
    renderWizard();
    await input("line one\nline two\nline three\nline four\nline five\nline six\nline seven");

    fireEvent.click(screen.getByRole("button", { name: "7행으로 이동" }));

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
    expect(editorHandle.revealLine1).toHaveBeenCalledOnce();
    expect(editorHandle.revealLine1).toHaveBeenCalledWith(7);
    expect(editorHandle.revealLine1.mock.invocationCallOrder[0]).toBeLessThan(
      scrollIntoView.mock.invocationCallOrder[0]!,
    );
  });

  it("editor가 마운트되지 않았거나 모델이 없으면 Pine 소스 section에 focus한다", async () => {
    const locatedError = ParsePreviewResponseSchema.parse({
      status: "error",
      pine_version: "v5",
      errors: [{ code: "SYNTAX_ERROR", message: "bad token", line: 3 }],
    });
    editorHandle.revealLine1.mockReturnValue(false);
    parseMock.mockResolvedValue(locatedError);
    renderWizard();
    await input("line one\nline two\nline three");
    const sourceSection = screen.getByLabelText("Pine 소스");
    const focus = vi.spyOn(sourceSection, "focus");

    fireEvent.click(screen.getByRole("button", { name: "3행으로 이동" }));

    expect(sourceSection).toHaveFocus();
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
    expect(focus.mock.invocationCallOrder[0]).toBeLessThan(
      scrollIntoView.mock.invocationCallOrder[0]!,
    );
  });

  it("같은 원문의 자동 검사 실패 뒤 수동 재검사가 성공하면 이전 오류를 지운다", async () => {
    parseMock.mockRejectedValueOnce(new Error("자동 검사 일시 실패")).mockResolvedValue(valid);
    renderWizard();
    await input("A");
    expect(screen.getByTestId("parse-error")).toHaveTextContent("자동 검사 일시 실패");
    fireEvent.click(screen.getByRole("button", { name: "파싱 검사" }));
    await tick();
    expect(screen.getByTestId("parse-error")).toBeEmptyDOMElement();
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeEnabled();
  });

  it("수동 성공 후 원문이 바뀌면 debounce 중에도 이전 판정으로 저장하지 않는다", async () => {
    parseMock.mockImplementation(async (source) => (source === "A" ? valid : invalid));
    renderWizard();
    await input("A");
    fireEvent.click(screen.getByRole("button", { name: "파싱 검사" }));
    await tick();
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeEnabled();
    fireEvent.change(screen.getByTestId("pine-editor"), { target: { value: "B" } });
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeDisabled();
    await tick(350);
    await tick();
    expect(screen.getByTestId("parse-status")).toHaveTextContent("error");
  });

  it("수동 실패 후 새 원문의 자동 검사가 성공하면 이전 오류를 지운다", async () => {
    parseMock.mockResolvedValue(valid);
    renderWizard();
    await input("A");
    parseMock.mockRejectedValueOnce(new Error("이전 요청 실패"));
    fireEvent.click(screen.getByRole("button", { name: "파싱 검사" }));
    await tick();
    expect(screen.getByTestId("parse-error")).toHaveTextContent("이전 요청 실패");
    await input("B");
    expect(screen.getByTestId("parse-error")).toBeEmptyDOMElement();
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeEnabled();
  });

  it("이전 원문의 수동 응답이 늦게 와도 현재 오류 판정을 덮지 않는다", async () => {
    parseMock.mockImplementation(async (source) => (source === "A" ? valid : invalid));
    renderWizard();
    await input("A");
    const manual = deferred();
    parseMock.mockReturnValueOnce(manual.promise);
    fireEvent.click(screen.getByRole("button", { name: "파싱 검사" }));
    await tick();
    await input("B");
    expect(screen.getByTestId("parse-status")).toHaveTextContent("error");
    await act(async () => {
      manual.resolve(valid);
    });
    await tick();
    expect(screen.getByTestId("parse-status")).toHaveTextContent("error");
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeDisabled();
  });

  it("이전 원문의 자동 응답이 늦게 와도 현재 성공 판정을 덮지 않는다", async () => {
    const previous = deferred();
    parseMock.mockImplementation((source) =>
      source === "A" ? previous.promise : Promise.resolve(valid),
    );
    renderWizard();
    await input("A");
    await input("B");
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeEnabled();
    await act(async () => {
      previous.resolve(invalid);
    });
    await tick();
    expect(screen.getByTestId("parse-status")).toHaveTextContent("ok");
    expect(screen.getByRole("button", { name: "판정 저장" })).toBeEnabled();
  });
});

// 기존 wizard 테스트의 패널 스텁은 loading 우선 렌더를 검사하지 못한다.
// 실제 훅 + 실제 패널을 연결해 완료된 수동 판정의 표시 권위를 검증한다.
const { ParseResultPanel: RealParseResultPanel } = await vi.importActual<
  typeof import("@/features/strategy/components/new/parse-result-panel")
>("@/features/strategy/components/new/parse-result-panel");

function CurrentSourcePanel({ source }: { source: string }) {
  const state = useCurrentSourceParse(source);
  return (
    <>
      <button type="button" onClick={state.parse}>
        수동 재검사
      </button>
      <output data-testid="current-loading">{String(state.loading)}</output>
      <RealParseResultPanel
        result={state.result}
        loading={state.loading}
        error={state.error}
        canSave={state.result?.status === "ok"}
        onSave={() => {}}
      />
    </>
  );
}
function renderCurrentPanel(source: string) {
  return render(
    <QueryClientProvider client={queryClient}>
      <CurrentSourcePanel source={source} />
    </QueryClientProvider>,
  );
}
function pendingParse() {
  let resolve!: (value: ParsePreviewResponse) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<ParsePreviewResponse>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

describe("현재 원문 수동 판정 — 실제 결과 패널", () => {
  it.each(["판정", "요청 실패"] as const)(
    "수동 성공을 즉시 표시하고 이전 자동 요청의 늦은 결과(%s)로 덮지 않는다",
    async (late) => {
      const auto = pendingParse();
      parseMock.mockReturnValueOnce(auto.promise).mockResolvedValueOnce(valid);
      renderCurrentPanel("A");
      await tick();
      expect(screen.getByTestId("parse-skeleton")).toBeVisible();
      fireEvent.click(screen.getByRole("button", { name: "수동 재검사" }));
      await tick();
      await tick();
      expect(parseMock).toHaveBeenCalledTimes(2);
      expect(screen.queryByTestId("parse-skeleton")).toBeNull();
      expect(screen.getByTestId("parse-save")).toBeEnabled();
      expect(screen.getByTestId("current-loading")).toHaveTextContent("false");
      await act(async () => {
        if (late === "판정") auto.resolve(invalid);
        else auto.reject(new Error("이전 자동 요청 실패"));
      });
      await tick();
      expect(screen.getByTestId("parse-save")).toBeEnabled();
      expect(screen.queryByTestId("parse-request-error")).toBeNull();
    },
  );

  it("현재 원문 수동 요청이 진행 중이면 기존 자동 성공을 표시하지 않는다", async () => {
    const manual = pendingParse();
    parseMock.mockResolvedValueOnce(valid).mockReturnValueOnce(manual.promise);
    renderCurrentPanel("A");
    await tick();
    await tick();
    expect(screen.getByTestId("parse-save")).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "수동 재검사" }));
    await tick();
    expect(screen.getByTestId("parse-skeleton")).toBeVisible();
    expect(screen.queryByTestId("parse-save")).toBeNull();
    await act(async () => manual.resolve(valid));
    await tick();
    expect(screen.getByTestId("parse-save")).toBeEnabled();
  });

  it("이전 원문의 수동 요청이 진행 중이어도 현재 원문의 자동 성공을 표시한다", async () => {
    const manual = pendingParse();
    parseMock
      .mockResolvedValueOnce(valid)
      .mockReturnValueOnce(manual.promise)
      .mockResolvedValue(valid);
    const { rerender } = renderCurrentPanel("A");
    await tick();
    await tick();
    fireEvent.click(screen.getByRole("button", { name: "수동 재검사" }));
    await tick();
    rerender(
      <QueryClientProvider client={queryClient}>
        <CurrentSourcePanel source="B" />
      </QueryClientProvider>,
    );
    await tick(350);
    await tick();
    expect(screen.queryByTestId("parse-skeleton")).toBeNull();
    expect(screen.getByTestId("parse-save")).toBeEnabled();
    await act(async () => manual.resolve(invalid));
    await tick();
    expect(screen.getByTestId("parse-save")).toBeEnabled();
  });

  it("현재 수동 요청이 실패로 완료되면 loading을 끝내고 해당 오류를 유지한다", async () => {
    const auto = pendingParse();
    parseMock.mockReturnValueOnce(auto.promise).mockRejectedValueOnce(new Error("수동 요청 실패"));
    renderCurrentPanel("A");
    await tick();
    fireEvent.click(screen.getByRole("button", { name: "수동 재검사" }));
    await tick();
    await tick();
    expect(screen.getByTestId("parse-request-error")).toHaveTextContent("수동 요청 실패");
    expect(screen.getByTestId("current-loading")).toHaveTextContent("false");
    expect(screen.queryByTestId("parse-skeleton")).toBeNull();
    await act(async () => auto.resolve(valid));
    await tick();
    expect(screen.getByTestId("parse-request-error")).toHaveTextContent("수동 요청 실패");
    expect(screen.queryByTestId("parse-save")).toBeNull();
  });
});
