// 수동 편집 → 저장 버전 → 고정 정책 백테스트 여정. API와 인증만 대체하며 실제 훅을 사용한다.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
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
} from "@/features/strategy/code-schemas";
import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";
import { ApiError, type RequestOptions } from "@/lib/api-client";
import { CodeWorkspace } from "../code-workspace";

const STRATEGY_ID = "11111111-1111-4111-8111-111111111111";
const SECOND_ID = "44444444-4444-4444-8444-444444444444";
const BACKTEST_ID = "33333333-3333-4333-8333-333333333333";
const clients: QueryClient[] = [];

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

function setup(items: CodeStrategy[] = []) {
  let stored = items;
  let version = 0;
  mocks.apiFetch.mockImplementation(async (path: string, options?: RequestOptions) => {
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
    return { items: stored, total: stored.length };
  });
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  clients.push(client);
  const view = render(
    <QueryClientProvider client={client}>
      <CodeWorkspace />
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
    expect(mocks.apiFetch).toHaveBeenLastCalledWith("/api/v1/strategies/code", {
      token: "second-token",
    });
    expect(client.getQueryData(codeStrategyKeys.list("user-1"))).toMatchObject({ total: 1 });
  });
});
