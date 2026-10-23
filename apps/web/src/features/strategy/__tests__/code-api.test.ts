// 수동 코드 저장·백테스트의 요청 정책과 응답 검증만 검사한다. 생성 API는 호출하지 않는다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import { ApiError } from "@/lib/api-client";
import {
  generateCodeStrategy,
  listCodeStrategies,
  saveCodeStrategy,
  submitCodeBacktest,
} from "../code-api";
import { getCodeResultStrategy } from "../code-result-api";
import { createBacktest } from "@/features/backtest/api";
import type { CodeLanguage, SaveCodeStrategy } from "../code-schemas";

const STRATEGY_ID = "11111111-1111-4111-8111-111111111111";
const VERSION_ID = "22222222-2222-4222-8222-222222222222";
const BACKTEST_ID = "33333333-3333-4333-8333-333333333333";
const TOKEN = "test-token";

function request(language: CodeLanguage = "python"): SaveCodeStrategy {
  return {
    name: "검토한 전략",
    symbol: "BTC/USDT",
    timeframe: "1h",
    code: {
      schema_version: 1,
      execution_policy: "code_v1",
      language,
      source_code: "manual source",
      warmup_bars: 200,
      params: { length: 20 },
      provenance: { origin: "manual_editor" },
    },
    settings: {
      schema_version: 1,
      leverage: 1,
      margin_mode: "cross",
      position_size_pct: 10,
      fill_timing: "next_bar_open",
      max_trigger_breach_pct: null,
      max_reversal_overshoot_ratio: null,
    },
  };
}

function response(language: CodeLanguage = "python") {
  const body = request(language);
  return {
    id: STRATEGY_ID,
    name: body.name,
    description: null,
    symbol: body.symbol,
    timeframe: body.timeframe,
    is_archived: false,
    settings: body.settings,
    version: {
      ...body.code,
      id: VERSION_ID,
      source_hash: "a".repeat(64),
      execution_hash: "b".repeat(64),
      created_at: "2026-01-01T00:00:00Z",
    },
  };
}

afterEach(() => {
  apiFetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("수동 코드 전략 API", () => {
  it("Gemini Python preview 요청은 저장과 별도이며 미보고 모델·usage를 보존한다", async () => {
    const preview = {
      status: "preview",
      code: request().code,
      assumptions: ["완료 봉에서 판단합니다."],
      provider: "gemini",
      requested_model: "configured-model",
      actual_model: null,
      usage: null,
    };
    apiFetchMock.mockResolvedValueOnce(preview);
    const body = { prompt: "빠른 평균이 느린 평균을 돌파하면 진입", warmup_bars: 200, params: {} };
    expect(await generateCodeStrategy(body, TOKEN)).toEqual(preview);
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/code/generate", {
      method: "POST",
      token: TOKEN,
      body,
    });
  });

  it("짧은 생성 요청은 전송 전에, Pine preview는 응답 검증에서 거절한다", async () => {
    await expect(
      generateCodeStrategy({ prompt: "짧음", warmup_bars: 200, params: {} }, TOKEN),
    ).rejects.toThrow();
    expect(apiFetchMock).not.toHaveBeenCalled();
    apiFetchMock.mockResolvedValueOnce({
      status: "preview",
      code: request("pine").code,
      assumptions: [],
      provider: "gemini",
      requested_model: "configured-model",
      actual_model: null,
      usage: null,
    });
    await expect(
      generateCodeStrategy(
        { prompt: "충분히 자세한 생성 조건입니다", warmup_bars: 200, params: {} },
        TOKEN,
      ),
    ).rejects.toThrow();
  });

  it.each(["python", "typescript", "pine"] as const)(
    "목록의 %s 버전을 검증하고 토큰을 전달한다",
    async (language) => {
      apiFetchMock.mockResolvedValueOnce({ items: [response(language)], total: 1 });
      const result = await listCodeStrategies(TOKEN);
      expect(result.items[0]?.version.language).toBe(language);
      expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/code", { token: TOKEN });
    },
  );

  it.each([null, STRATEGY_ID])("새 전략과 새 버전을 올바른 endpoint에 저장한다: %s", async (id) => {
    apiFetchMock.mockResolvedValueOnce(response());
    await saveCodeStrategy(id, request(), TOKEN);
    expect(apiFetchMock).toHaveBeenCalledWith(
      id ? `/api/v1/strategies/code/${id}` : "/api/v1/strategies/code",
      { method: id ? "PUT" : "POST", token: TOKEN, body: request() },
    );
  });

  it("결과의 코드 상세 조회도 응답 언어를 검증한다", async () => {
    apiFetchMock.mockResolvedValueOnce(response());
    expect((await getCodeResultStrategy(STRATEGY_ID, TOKEN)).id).toBe(STRATEGY_ID);
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/strategies/code/${STRATEGY_ID}`, {
      token: TOKEN,
    });
    const payload = response();
    apiFetchMock.mockResolvedValueOnce({
      ...payload,
      version: { ...payload.version, language: "javascript" },
    });
    await expect(getCodeResultStrategy(STRATEGY_ID, TOKEN)).rejects.toThrow();
  });

  it("공통 백테스트 클라이언트의 Zod 검증 뒤에도 코드 재실행 정책과 수량이 전달된다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      status: "queued",
      created_at: "2026-01-01T00:00:00Z",
    });
    await createBacktest(
      {
        strategy_id: STRATEGY_ID,
        execution_policy: "code_v1",
        symbol: "BTC/USDT",
        timeframe: "1h",
        period_start: "2026-01-01T00:00:00Z",
        period_end: "2026-02-01T00:00:00Z",
        initial_capital: 10000,
        leverage: 1,
        fees_pct: 0.0004,
        slippage_pct: 0.0002,
        include_funding: true,
        fill_timing: "next_bar_open",
        default_qty_type: "strategy.percent_of_equity",
        default_qty_value: 17,
      },
      TOKEN,
    );
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests",
      expect.objectContaining({
        method: "POST",
        token: TOKEN,
        body: expect.objectContaining({ execution_policy: "code_v1", default_qty_value: 17 }),
      }),
    );
  });

  it("지원하지 않는 응답 언어는 목록과 저장 양쪽에서 거절한다", async () => {
    const invalid = response();
    const payload = { ...invalid, version: { ...invalid.version, language: "javascript" } };
    apiFetchMock.mockResolvedValueOnce({ items: [payload], total: 1 });
    await expect(listCodeStrategies(TOKEN)).rejects.toThrow();
    apiFetchMock.mockResolvedValueOnce(payload);
    await expect(saveCodeStrategy(null, request(), TOKEN)).rejects.toThrow();
  });

  it("저장 요청과 응답에서 실행 원문의 앞뒤 공백과 줄바꿈을 보존한다", async () => {
    const source = "  manual source\n\t";
    const body = request();
    body.code.source_code = source;
    const payload = response();
    payload.version.source_code = source;
    apiFetchMock.mockResolvedValueOnce(payload);
    expect((await saveCodeStrategy(null, body, TOKEN)).version.source_code).toBe(source);
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/code", {
      method: "POST",
      token: TOKEN,
      body,
    });
  });

  it("공백만 있는 원문은 저장 요청 전에 거절한다", async () => {
    const body = request();
    body.code.source_code = " \n\t";
    await expect(saveCodeStrategy(null, body, TOKEN)).rejects.toThrow();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it.each([[], null, "not an object"])(
    "JSON 객체가 아닌 params는 요청 전에 거절한다: %s",
    async (params) => {
      const body = request();
      const invalid = { ...body, code: { ...body.code, params } } as unknown as SaveCodeStrategy;
      await expect(saveCodeStrategy(null, invalid, TOKEN)).rejects.toThrow();
      expect(apiFetchMock).not.toHaveBeenCalled();
    },
  );

  it("저장 오류의 status·code·사용자 메시지를 그대로 보존한다", async () => {
    const error = new ApiError(422, "invalid_code", "저장 실패", {
      detail: "코드가 비어 있습니다.",
    });
    apiFetchMock.mockRejectedValueOnce(error);
    await expect(saveCodeStrategy(null, request(), TOKEN)).rejects.toBe(error);
  });

  it("202 응답을 검증하고 코드 실행 정책·1배·펀딩·다음 시가를 고정한다", async () => {
    const { apiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
    apiFetchMock.mockImplementation(apiFetch);
    const accepted = {
      backtest_id: BACKTEST_ID,
      status: "queued",
      created_at: "2026-01-01T00:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(accepted), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    const body = {
      strategy_id: STRATEGY_ID,
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "2026-01-01T00:00:00Z",
      period_end: "2026-02-01T00:00:00Z",
      initial_capital: "10000",
      position_size_pct: 10,
    };
    await expect(submitCodeBacktest(body, TOKEN)).resolves.toEqual(accepted);
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/backtests$/);
    expect(JSON.parse(String(options.body))).toEqual({
      ...body,
      execution_policy: "code_v1",
      fill_timing: "next_bar_open",
      leverage: "1",
      include_funding: true,
    });
    expect(options.headers).toMatchObject({ Authorization: `Bearer ${TOKEN}` });
  });

  it("백테스트 ID가 없는 응답은 성공으로 취급하지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ status: "queued", created_at: "2026-01-01T00:00:00Z" });
    await expect(
      submitCodeBacktest(
        {
          strategy_id: STRATEGY_ID,
          symbol: "BTC/USDT",
          timeframe: "1h",
          period_start: "2026-01-01T00:00:00Z",
          period_end: "2026-02-01T00:00:00Z",
          initial_capital: "10000",
          position_size_pct: 10,
        },
        TOKEN,
      ),
    ).rejects.toThrow();
  });
});
