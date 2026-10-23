// 수동 편집 → 저장 버전 → 고정 정책 백테스트 여정. API와 인증만 대체하며 실제 훅을 사용한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api-client")>()),
  apiFetch: mocks.apiFetch,
}));

import {
  codeStrategyKeys,
  type CodeStrategy,
  type SaveCodeStrategy,
  type GenerateCodeStrategyResponse,
} from "@/features/strategy/code-schemas";
import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";
import { getAuthToken } from "@/lib/auth-client";
import { ApiError, type RequestOptions } from "@/lib/api-client";
import { CodeWorkspace } from "../code-workspace";
import type { ExchangeAccount } from "@/features/trading/schemas";

const STRATEGY_ID = "11111111-1111-4111-8111-111111111111";
const SECOND_ID = "44444444-4444-4444-8444-444444444444";
const BACKTEST_ID = "33333333-3333-4333-8333-333333333333";
const clients: QueryClient[] = [];
const ACCOUNT_ID = "66666666-6666-4666-8666-666666666666";
const demoAccount: ExchangeAccount = {
  id: ACCOUNT_ID,
  exchange: "bybit",
  mode: "demo",
  label: "검증 계정",
  api_key_masked: "***test",
  exchange_uid: null,
  read_only: false,
  created_at: "2026-01-01T00:00:00Z",
};

function saved(name = "이전 전략", id = STRATEGY_ID): CodeStrategy {
  return {
    id,
    name,
    description: null,
    symbol: "BTC/USDT",
    timeframe: "1h",
    is_archived: false,
    settings: {
      schema_version: 1,
      leverage: 1,
      margin_mode: "cross",
      position_size_pct: 10,
      fill_timing: "next_bar_open",
      max_trigger_breach_pct: null,
      max_reversal_overshoot_ratio: null,
    },
    version: {
      id: "22222222-2222-4222-8222-222222222222",
      schema_version: 1,
      execution_policy: "code_v1",
      language: "python",
      source_code: `manual source ${name}`,
      warmup_bars: 200,
      params: { length: 20 },
      provenance: { origin: "manual_editor" },
      source_hash: "a".repeat(64),
      execution_hash: "b".repeat(64),
      created_at: "2026-01-01T00:00:00Z",
    },
  };
}

function generatedPreview(): GenerateCodeStrategyResponse {
  return {
    status: "preview",
    code: {
      schema_version: 1,
      execution_policy: "code_v1",
      language: "python",
      source_code: 'def on_bar(ctx, state):\n    return {"action": "hold"}\n',
      warmup_bars: 40,
      params: { fast: 10, slow: 30 },
      provenance: {
        kind: "gemini_generated",
        provider: "gemini",
        requested_model: "configured-model",
        actual_model: null,
      },
    },
    assumptions: ["완료 봉에서만 진입 조건을 판단합니다."],
    provider: "gemini",
    requested_model: "configured-model",
    actual_model: null,
    usage: { input_tokens: 100, output_tokens: 20, thinking_tokens: null, total_tokens: null },
  };
}

function setup(
  items: CodeStrategy[] = [],
  accounts: ExchangeAccount[] = [],
  initialStrategyId?: string,
  { listGate, staleTime = 0 }: { listGate?: Promise<void>; staleTime?: number } = {},
) {
  let stored = items;
  let version = 0;
  mocks.apiFetch.mockImplementation(async (path: string, options?: RequestOptions) => {
    if (path === "/api/v1/strategies/code/generate") return generatedPreview();
    if (path === "/api/v1/exchange-accounts") return { items: accounts };
    if (path === "/api/v1/live-sessions")
      return {
        id: SECOND_ID,
        user_id: ACCOUNT_ID,
        strategy_id: STRATEGY_ID,
        exchange_account_id: ACCOUNT_ID,
        symbol: "BTC/USDT",
        interval: "1h",
        is_active: true,
        last_evaluated_bar_time: null,
        created_at: "2026-01-01T00:00:00Z",
        deactivated_at: null,
      };
    if (path === "/api/v1/backtests") {
      return { backtest_id: BACKTEST_ID, status: "queued", created_at: "2026-01-01T00:00:00Z" };
    }
    if (options?.method === "POST" || options?.method === "PUT") {
      const body = options.body as SaveCodeStrategy;
      version += 1;
      const item = {
        ...saved(body.name),
        symbol: body.symbol,
        timeframe: body.timeframe,
        settings: body.settings,
        version: {
          ...saved().version,
          ...body.code,
          id:
            version === 1
              ? "22222222-2222-4222-8222-222222222222"
              : "55555555-5555-4555-8555-555555555555",
        },
      };
      stored = [item];
      return item;
    }
    if (path === "/api/v1/strategies/code") await listGate;
    return { items: stored, total: stored.length };
  });
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime },
      mutations: { retry: false },
    },
  });
  clients.push(client);
  const view = render(
    <QueryClientProvider client={client}>
      <CodeWorkspace initialStrategyId={initialStrategyId} />
    </QueryClientProvider>,
  );
  return { ...view, client };
}

async function ready() {
  await screen.findByRole("heading", { name: "코드 전략" });
}

function fillDraft() {
  fireEvent.change(screen.getByLabelText("전략 이름"), { target: { value: "수동 전략" } });
  fireEvent.change(screen.getByLabelText("소스 코드"), { target: { value: "manual version one" } });
}

beforeEach(() => {
  resetAuthMock();
});
afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  vi.clearAllMocks();
  resetAuthMock();
});

describe("코드 전략 작업 공간", () => {
  it("코드 목록을 기다리는 동안 계정 요청도 시작하고 완료 뒤 중복 요청하지 않는다", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    // 서비스 QueryProvider와 동일한 60초 신선도에서 prefetch 캐시를 공유한다.
    setup([saved()], [demoAccount], STRATEGY_ID, { listGate: gate, staleTime: 60_000 });
    try {
      await waitFor(() => {
        expect(mocks.apiFetch).toHaveBeenCalledWith("/api/v1/strategies/code", expect.anything());
        expect(mocks.apiFetch).toHaveBeenCalledWith("/api/v1/exchange-accounts", expect.anything());
      });
    } finally {
      release();
    }
    await ready();
    expect(
      mocks.apiFetch.mock.calls.filter(([path]) => path === "/api/v1/exchange-accounts"),
    ).toHaveLength(1);
  });

  it("기간만 편집할 때 긴 저장 원문을 다시 직렬화하지 않고 dirty 상태를 유지한다", async () => {
    const item = saved();
    item.version.source_code = "return hold\n".repeat(8000);
    setup([item], [], STRATEGY_ID);
    await ready();
    const stringify = vi.spyOn(JSON, "stringify");
    try {
      fireEvent.change(screen.getByLabelText("초기 자본 (USDT)"), { target: { value: "20000" } });
      expect(screen.getByText("저장한 원문과 일치합니다.")).toBeInTheDocument();
      expect(
        stringify.mock.calls.filter(
          ([value]) => value && typeof value === "object" && "source" in value,
        ),
      ).toHaveLength(0);
      fireEvent.change(screen.getByLabelText("소스 코드"), { target: { value: "changed source" } });
      expect(screen.getByText("변경 사항이 있습니다.")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("소스 코드"), {
        target: { value: item.version.source_code },
      });
      expect(screen.getByText("저장한 원문과 일치합니다.")).toBeInTheDocument();
    } finally {
      stringify.mockRestore();
    }
  });

  it("서버 렌더는 브라우저 인증 토큰과 코드 목록을 요청하지 않는다", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    clients.push(client);
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <CodeWorkspace />
      </QueryClientProvider>,
    );
    await Promise.resolve();
    expect(html).toContain("코드 전략을 불러오는 중");
    expect(getAuthToken).not.toHaveBeenCalled();
    expect(mocks.apiFetch).not.toHaveBeenCalled();
  });

  it("생성 preview는 명시 적용·저장·백테스트를 각각 눌러야 전진한다", async () => {
    setup();
    await ready();
    fillDraft();
    fireEvent.change(screen.getByLabelText("진입·청산 조건"), {
      target: { value: "빠른 평균이 느린 평균을 돌파하면 롱" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Python 초안 생성" }));
    await screen.findByTestId("code-generation-preview");
    expect(screen.getByLabelText("소스 코드")).toHaveValue("manual version one");
    expect(screen.getByText(/응답 모델:/)).toHaveTextContent("미보고 · 확인 안 됨");
    expect(screen.getByText(/토큰 사용량:/)).toHaveTextContent("사고 미보고");
    expect(
      mocks.apiFetch.mock.calls.filter(([, options]) => options?.method === "POST"),
    ).toHaveLength(1);
    expect(screen.getByRole("button", { name: "백테스트 실행" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "이 Python 초안 적용" }));
    expect(screen.getByLabelText("소스 코드")).toHaveValue(generatedPreview().code.source_code);
    expect(
      (screen.getByLabelText("소스 코드") as HTMLTextAreaElement).labels?.[0]?.textContent,
    ).toBe("소스 코드");
    expect(
      (screen.getByLabelText("파라미터 JSON") as HTMLTextAreaElement).labels?.[0]?.textContent,
    ).toBe("파라미터 JSON");
    expect(screen.getByLabelText("준비 봉 수")).toHaveValue(40);
    expect(screen.getByLabelText("실행 언어")).toHaveValue("python");
    expect(
      mocks.apiFetch.mock.calls.filter(([, options]) => options?.method === "POST"),
    ).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "전략 저장" }));
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/strategies/code",
      expect.objectContaining({
        body: expect.objectContaining({ code: generatedPreview().code }),
      }),
    );
    expect(
      mocks.apiFetch.mock.calls.some(
        ([path]) => path === "/api/v1/backtests" || path === "/api/v1/live-sessions",
      ),
    ).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "백테스트 실행" }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith(`/backtests/${BACKTEST_ID}`));
  });

  it.each(["source", "language", "params", "warmup"] as const)(
    "적용 후 %s를 수정하면 생성 출처를 수동 출처로 바꾼다",
    async (field) => {
      setup([saved()], [], STRATEGY_ID);
      await ready();
      fireEvent.change(screen.getByLabelText("진입·청산 조건"), {
        target: { value: "빠른 평균이 느린 평균을 돌파하면 롱" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Python 초안 생성" }));
      await screen.findByTestId("code-generation-preview");
      fireEvent.click(screen.getByRole("button", { name: "이 Python 초안 적용" }));
      const edit = {
        source: ["소스 코드", "changed source"],
        language: ["실행 언어", "typescript"],
        params: ["파라미터 JSON", '{"fast": 11, "slow": 30}'],
        warmup: ["준비 봉 수", "41"],
      }[field];
      fireEvent.change(screen.getByLabelText(edit[0]!), { target: { value: edit[1] } });
      fireEvent.click(screen.getByRole("button", { name: "새 버전 저장" }));
      await screen.findByText("저장한 원문과 일치합니다.");
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        `/api/v1/strategies/code/${STRATEGY_ID}`,
        expect.objectContaining({
          body: expect.objectContaining({
            code: expect.objectContaining({
              provenance: { origin: "manual_editor", parent_version_id: saved().version.id },
            }),
          }),
        }),
      );
    },
  );

  it("파라미터 JSON의 공백과 키 순서만 바꾸면 생성 출처를 보존한다", async () => {
    setup();
    await ready();
    fillDraft();
    fireEvent.change(screen.getByLabelText("진입·청산 조건"), {
      target: { value: "빠른 평균이 느린 평균을 돌파하면 롱" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Python 초안 생성" }));
    await screen.findByTestId("code-generation-preview");
    fireEvent.click(screen.getByRole("button", { name: "이 Python 초안 적용" }));
    fireEvent.change(screen.getByLabelText("파라미터 JSON"), {
      target: { value: '{ "slow": 30, "fast": 10 }' },
    });
    fireEvent.click(screen.getByRole("button", { name: "전략 저장" }));
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/strategies/code",
      expect.objectContaining({
        body: expect.objectContaining({
          code: expect.objectContaining({ provenance: generatedPreview().code.provenance }),
        }),
      }),
    );
  });

  it.each(["새 코드", "이전 전략 · Python"])(
    "생성 대기 중 %s로 이동하면 늦은 응답을 적용할 수 없다",
    async (button) => {
      setup([saved()]);
      await ready();
      const previous = mocks.apiFetch.getMockImplementation()!;
      let resolvePreview: (value: GenerateCodeStrategyResponse) => void = () => {};
      const pending = new Promise<GenerateCodeStrategyResponse>((resolve) => {
        resolvePreview = resolve;
      });
      mocks.apiFetch.mockImplementation((path: string, options?: RequestOptions) =>
        path === "/api/v1/strategies/code/generate" ? pending : previous(path, options),
      );
      fireEvent.change(screen.getByLabelText("진입·청산 조건"), {
        target: { value: "빠른 평균이 느린 평균을 돌파하면 롱" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Python 초안 생성" }));
      await screen.findByRole("button", { name: "Python 초안 만드는 중…" });
      fireEvent.click(screen.getByRole("button", { name: button }));
      await act(async () => resolvePreview(generatedPreview()));
      expect(screen.queryByTestId("code-generation-preview")).toBeNull();
      expect(screen.getByLabelText("진입·청산 조건")).toHaveValue("");
      expect(screen.getByLabelText("소스 코드")).toHaveValue(
        button === "새 코드" ? "" : saved().version.source_code,
      );
    },
  );

  it("생성 quota 실패는 한 번만 요청하고 원문과 실행 상태를 보존한다", async () => {
    setup();
    await ready();
    fillDraft();
    mocks.apiFetch.mockRejectedValueOnce(
      new ApiError(429, "code_generate_quota", "무료 한도를 확인하세요."),
    );
    fireEvent.change(screen.getByLabelText("진입·청산 조건"), {
      target: { value: "빠른 평균이 느린 평균을 돌파하면 롱" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Python 초안 생성" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("무료 한도를 확인하세요.");
    expect(
      mocks.apiFetch.mock.calls.filter(([path]) => path === "/api/v1/strategies/code/generate"),
    ).toHaveLength(1);
    expect(screen.getByLabelText("소스 코드")).toHaveValue("manual version one");
    expect(screen.queryByTestId("code-generation-preview")).toBeNull();
    expect(screen.getByRole("button", { name: "백테스트 실행" })).toBeDisabled();
  });

  it("생성 응답 전에 사용자가 바뀌면 이전 사용자의 preview를 보이지 않는다", async () => {
    const { client, rerender } = setup();
    await ready();
    let resolvePreview: (value: GenerateCodeStrategyResponse) => void = () => {};
    const pending = new Promise<GenerateCodeStrategyResponse>((resolve) => {
      resolvePreview = resolve;
    });
    const previous = mocks.apiFetch.getMockImplementation()!;
    mocks.apiFetch.mockImplementation((path: string, options?: RequestOptions) =>
      path === "/api/v1/strategies/code/generate" ? pending : previous(path, options),
    );
    fireEvent.change(screen.getByLabelText("진입·청산 조건"), {
      target: { value: "빠른 평균이 느린 평균을 돌파하면 롱" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Python 초안 생성" }));
    await screen.findByRole("button", { name: "Python 초안 만드는 중…" });
    authMockState.userId = "user-2";
    authMockState.token = "second-token";
    await act(async () =>
      rerender(
        <QueryClientProvider client={client}>
          <CodeWorkspace />
        </QueryClientProvider>,
      ),
    );
    await ready();
    await act(async () => resolvePreview(generatedPreview()));
    expect(screen.queryByTestId("code-generation-preview")).toBeNull();
    expect(screen.getByLabelText("진입·청산 조건")).toHaveValue("");
    expect(screen.getByLabelText("소스 코드")).toHaveValue("");
  });

  it("저장 → dirty 실행 금지 → 새 버전 저장 → 고정 정책 요청 → 결과 화면으로 이동한다", async () => {
    const { client } = setup();
    await ready();
    const run = screen.getByRole("button", { name: "백테스트 실행" });
    expect(run).toBeDisabled();
    fillDraft();
    fireEvent.click(screen.getByRole("button", { name: "전략 저장" }));
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(run).toBeEnabled();
    expect(client.getQueryData(codeStrategyKeys.list("user-1"))).toMatchObject({ total: 1 });
    fireEvent.change(screen.getByLabelText("소스 코드"), {
      target: { value: "manual version two" },
    });
    expect(run).toBeDisabled();
    fireEvent.click(run);
    expect(mocks.apiFetch.mock.calls.filter(([path]) => path === "/api/v1/backtests")).toHaveLength(
      0,
    );
    fireEvent.click(screen.getByRole("button", { name: "새 버전 저장" }));
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      `/api/v1/strategies/code/${STRATEGY_ID}`,
      expect.objectContaining({
        method: "PUT",
        token: "test-token",
        body: expect.objectContaining({
          code: expect.objectContaining({
            source_code: "manual version two",
            execution_policy: "code_v1",
          }),
        }),
      }),
    );
    fireEvent.change(screen.getByLabelText("시작일 (UTC)"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("종료일 (UTC·미포함)"), {
      target: { value: "2026-02-01" },
    });
    fireEvent.click(run);
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith(`/backtests/${BACKTEST_ID}`));
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/backtests",
      expect.objectContaining({
        method: "POST",
        token: "test-token",
        body: expect.objectContaining({
          strategy_id: STRATEGY_ID,
          strategy_version_id: "55555555-5555-4555-8555-555555555555",
          period_start: "2026-01-01T00:00:00Z",
          period_end: "2026-02-01T00:00:00Z",
          execution_policy: "code_v1",
          fill_timing: "next_bar_open",
          leverage: "1",
          include_funding: true,
        }),
      }),
    );
  });

  it("목록의 최신 버전이 바뀌어도 화면에서 검토한 버전으로 백테스트를 요청한다", async () => {
    const original = saved();
    const { client } = setup([original], [], STRATEGY_ID);
    await ready();
    await screen.findByText("저장한 원문과 일치합니다.");
    act(() => {
      client.setQueryData(codeStrategyKeys.list("user-1"), {
        items: [{ ...original, version: { ...original.version, id: SECOND_ID } }],
        total: 1,
      });
    });
    fireEvent.change(screen.getByLabelText("시작일 (UTC)"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("종료일 (UTC·미포함)"), {
      target: { value: "2026-02-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: "백테스트 실행" }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith(`/backtests/${BACKTEST_ID}`));
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/backtests",
      expect.objectContaining({
        body: expect.objectContaining({ strategy_version_id: original.version.id }),
      }),
    );
  });

  it.each(["{", "[]"])("파라미터 오류 %s는 저장 요청 전에 표시한다", async (params) => {
    setup();
    await ready();
    fillDraft();
    fireEvent.change(screen.getByLabelText("파라미터 JSON"), { target: { value: params } });
    fireEvent.click(screen.getByRole("button", { name: "전략 저장" }));
    expect(await screen.findByRole("alert")).not.toBeEmptyDOMElement();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
    expect(screen.getByRole("button", { name: "백테스트 실행" })).toBeDisabled();
  });

  it("저장 요청 중 연속 선택과 원문 편집을 차단한다", async () => {
    setup([saved("저장한 전략")]);
    await ready();
    fillDraft();
    let resolveSave: (value: CodeStrategy) => void = () => {};
    const pending = new Promise<CodeStrategy>((resolve) => {
      resolveSave = resolve;
    });
    mocks.apiFetch.mockReturnValueOnce(pending);
    fireEvent.click(screen.getByRole("button", { name: "전략 저장" }));
    await screen.findByRole("button", { name: "저장 중…" });
    expect(screen.getByLabelText("소스 코드")).toBeDisabled();
    expect(screen.getByRole("button", { name: "새 코드" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "저장한 전략 · Python" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "저장한 전략 · Python" }));
    expect(screen.getByLabelText("전략 이름")).toHaveValue("수동 전략");
    const item = saved("수동 전략");
    item.version.source_code = "manual version one";
    await act(async () => {
      resolveSave(item);
    });
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(screen.getByRole("button", { name: "새 코드" })).toBeEnabled();
  });

  it("잘못된 백테스트 기간은 오류를 표시하고 요청하지 않는다", async () => {
    setup([saved("기간 검증")]);
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "기간 검증 · Python" }));
    fireEvent.change(screen.getByLabelText("시작일 (UTC)"), { target: { value: "2026-02-01" } });
    fireEvent.change(screen.getByLabelText("종료일 (UTC·미포함)"), {
      target: { value: "2026-01-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: "백테스트 실행" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("종료일은 시작일 뒤여야 합니다.");
    expect(mocks.apiFetch.mock.calls.some(([path]) => path === "/api/v1/backtests")).toBe(false);
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it("서버 저장 오류를 표시하고 전략을 다시 선택하면 오류와 dirty 상태를 지운다", async () => {
    setup([saved("첫 전략"), saved("둘째 전략", SECOND_ID)]);
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "첫 전략 · Python" }));
    fireEvent.change(screen.getByLabelText("소스 코드"), {
      target: { value: "invalid revised source" },
    });
    mocks.apiFetch.mockRejectedValueOnce(
      new ApiError(422, "invalid_code", "저장 실패", { detail: "코드 원문을 확인하세요." }),
    );
    fireEvent.click(screen.getByRole("button", { name: "새 버전 저장" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("코드 원문을 확인하세요.");
    fireEvent.click(screen.getByRole("button", { name: "둘째 전략 · Python" }));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByLabelText("소스 코드")).toHaveValue("manual source 둘째 전략");
    expect(screen.getByRole("button", { name: "백테스트 실행" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "새 코드" }));
    expect(screen.getByLabelText("전략 이름")).toHaveValue("");
    expect(screen.getByLabelText("소스 코드")).toHaveValue("");
    expect(screen.getByRole("button", { name: "백테스트 실행" })).toBeDisabled();
  });

  it("로그아웃과 사용자 변경은 목록 캐시와 선택한 원문을 분리한다", async () => {
    const { client, rerender } = setup([saved("사용자 A 원문")]);
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "사용자 A 원문 · Python" }));
    expect(screen.getByLabelText("소스 코드")).toHaveValue("manual source 사용자 A 원문");
    authMockState.userId = null;
    authMockState.token = null;
    mocks.apiFetch.mockResolvedValue({ items: [], total: 0 });
    await act(async () => {
      rerender(
        <QueryClientProvider client={client}>
          <CodeWorkspace />
        </QueryClientProvider>,
      );
    });
    await screen.findByText("아직 저장한 코드 전략이 없습니다.");
    expect(client.getQueryData(codeStrategyKeys.list("anon"))).toEqual({ items: [], total: 0 });
    expect(screen.getByLabelText("소스 코드")).toHaveValue("");
    expect(screen.getByRole("button", { name: "백테스트 실행" })).toBeDisabled();
    authMockState.userId = "user-2";
    authMockState.token = "second-token";
    await act(async () => {
      rerender(
        <QueryClientProvider client={client}>
          <CodeWorkspace />
        </QueryClientProvider>,
      );
    });
    await waitFor(() =>
      expect(client.getQueryData(codeStrategyKeys.list("user-2"))).toEqual({ items: [], total: 0 }),
    );
    expect(mocks.apiFetch).toHaveBeenCalledWith("/api/v1/strategies/code", {
      token: "second-token",
    });
    expect(client.getQueryData(codeStrategyKeys.list("user-1"))).toMatchObject({ total: 1 });
  });

  it("선택 링크의 저장 버전을 불러와 주문 가능한 Demo 계정과 버전을 고정한다", async () => {
    setup([saved()], [demoAccount], STRATEGY_ID);
    await ready();
    expect(screen.getByLabelText("소스 코드")).toHaveValue("manual source 이전 전략");
    const start = screen.getByRole("button", { name: "데모 자동매매 시작" });
    expect(start).toBeDisabled();
    await screen.findByRole("option", { name: "검증 계정 · ***test" });
    fireEvent.change(screen.getByLabelText("Bybit Demo 계정"), { target: { value: ACCOUNT_ID } });
    expect(start).toBeEnabled();
    fireEvent.click(start);
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/trading"));
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/live-sessions",
      expect.objectContaining({
        method: "POST",
        body: {
          strategy_id: STRATEGY_ID,
          strategy_version_id: saved().version.id,
          exchange_account_id: ACCOUNT_ID,
          source_policy: "code_v1",
          symbol: "BTC/USDT",
          interval: "1h",
        },
      }),
    );
  });

  it("실계정·조회 전용·권한 미확인 계정은 제외하고 dirty와 4h 전략은 데모 시작을 막는다", async () => {
    setup(
      [saved()],
      [
        demoAccount,
        { ...demoAccount, id: SECOND_ID, mode: "live" },
        { ...demoAccount, id: STRATEGY_ID, read_only: true },
        { ...demoAccount, id: BACKTEST_ID, read_only: null },
      ],
      STRATEGY_ID,
    );
    await ready();
    await screen.findByRole("option", { name: "검증 계정 · ***test" });
    expect(screen.getByLabelText("Bybit Demo 계정").querySelectorAll("option")).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Bybit Demo 계정"), { target: { value: ACCOUNT_ID } });
    const start = screen.getByRole("button", { name: "데모 자동매매 시작" });
    fireEvent.change(screen.getByLabelText("소스 코드"), { target: { value: "changed" } });
    expect(start).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "이전 전략 · Python" }));
    fireEvent.change(screen.getByLabelText("신호 주기"), { target: { value: "4h" } });
    fireEvent.click(screen.getByRole("button", { name: "새 버전 저장" }));
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(start).toBeDisabled();
    expect(mocks.apiFetch.mock.calls.some(([path]) => path === "/api/v1/live-sessions")).toBe(
      false,
    );
  });

  it("직접 수정한 생성 코드는 수동 편집 출처로 기록하고 저장한 마진 모드를 보존한다", async () => {
    const item = saved();
    item.version.provenance = { origin: "sol_generation", model: "gpt-6.1-sol" };
    item.settings!.margin_mode = "isolated";
    setup([item], [], STRATEGY_ID);
    await ready();
    fireEvent.change(screen.getByLabelText("소스 코드"), {
      target: { value: "edited generated source" },
    });
    fireEvent.click(screen.getByRole("button", { name: "새 버전 저장" }));
    await screen.findByText("저장한 원문과 일치합니다.");
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      `/api/v1/strategies/code/${STRATEGY_ID}`,
      expect.objectContaining({
        body: expect.objectContaining({
          settings: expect.objectContaining({ margin_mode: "isolated" }),
          code: expect.objectContaining({
            provenance: { origin: "manual_editor", parent_version_id: item.version.id },
          }),
        }),
      }),
    );
  });
});
