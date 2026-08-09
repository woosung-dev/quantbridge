// e2e 가 `page.route` 로 돌려주는 응답이 **실제 클라이언트 계약**을 만족하는지 동결한다.
//
// ★왜 필요한가. playwright 의 mock 은 아무 JSON 이나 돌려줄 수 있고, 화면은 query 가
// 죽어도 폴백으로 계속 그려진다. 그래서 스키마와 어긋난 mock 위에서도 e2e 는 초록이다 —
// r1 의 전략 목록 mock 이 정확히 그랬다(`limit`·`total_pages`·필수 전략 필드 누락으로
// `StrategyListResponseSchema.parse` 가 죽는데 spec 은 3본 모두 통과했다).
// 그 거짓 초록을 막는 것은 e2e 가 아니라 **대입 그 자체**다.
//
// ★스키마를 여기에 다시 쓰지 않는다 — 실제 모듈을 import 한다. 복사하면 이 테스트는
// 배선이 아니라 내 복사본을 검사하게 된다(이 레포가 반복해서 밟은 함정).

import { describe, expect, it } from "vitest";

import {
  MOCK_EXCHANGE_ACCOUNT_LIST,
  MOCK_LIVE_SESSION_EVENTS,
  MOCK_LIVE_SESSION_LIST,
  MOCK_LIVE_SESSION_STATE,
  MOCK_OUTCOME_PARITY,
  MOCK_OUTCOME_PARITY_LONG_LEDGER_SUB,
  MOCK_STRATEGY_LIST,
} from "../../../../e2e/fixtures/outcome-parity";
import { ExchangeAccountListResponseSchema } from "../../trading/schemas";
import { StrategyListResponseSchema } from "../../strategy/schemas";
import {
  LiveSessionListResponseSchema,
  LiveSignalEventListResponseSchema,
  LiveSignalStateSchema,
  OutcomeParityResponseSchema,
} from "../schemas";

describe("outcome-parity e2e fixture 계약", () => {
  it("전략 목록 mock 이 StrategyListResponseSchema 를 통과한다", () => {
    expect(() => StrategyListResponseSchema.parse(MOCK_STRATEGY_LIST)).not.toThrow();
  });

  it("거래소 계정 mock 이 ExchangeAccountListResponseSchema 를 통과한다", () => {
    expect(() => ExchangeAccountListResponseSchema.parse(MOCK_EXCHANGE_ACCOUNT_LIST)).not.toThrow();
  });

  it("라이브 세션 목록·상태·이벤트 mock 이 각 스키마를 통과한다", () => {
    expect(() => LiveSessionListResponseSchema.parse(MOCK_LIVE_SESSION_LIST)).not.toThrow();
    expect(() => LiveSignalStateSchema.parse(MOCK_LIVE_SESSION_STATE)).not.toThrow();
    expect(() => LiveSignalEventListResponseSchema.parse(MOCK_LIVE_SESSION_EVENTS)).not.toThrow();
  });

  it("outcome-parity mock 이 OutcomeParityResponseSchema 를 통과한다", () => {
    expect(() => OutcomeParityResponseSchema.parse(MOCK_OUTCOME_PARITY)).not.toThrow();
  });

  // ★이 검사의 판별력 — "아무 JSON 이나 통과시키는 검사" 가 아님을 음성 대조로 못 박는다.
  // 아래 모양이 r1 이 실제로 라우팅하던 응답이다. codex 가 제시한 반증 방법 그대로 대입한다.
  it("r1 의 축약 전략 mock 은 같은 스키마에서 실제로 죽는다", () => {
    const r1Shape = {
      items: [
        {
          id: "c0000000-0000-4000-8000-000000000001",
          name: "BTC RSI Mean Reversion",
          tags: [],
          parse_status: "ok",
          updated_at: "2026-08-06T00:00:00Z",
        },
      ],
      total: 1,
      page: 0,
      page_size: 20,
    };

    expect(() => StrategyListResponseSchema.parse(r1Shape)).toThrow();
  });

  // 픽스처가 겨냥한 비대칭(BL-606) 이 살아 있는지 — 값이 흐려지면 spec 이 재는 대상이 바뀐다.
  it("픽스처는 세션 축 0 · 전략 축 41 의 비대칭을 유지한다", () => {
    const parsed = OutcomeParityResponseSchema.parse(MOCK_OUTCOME_PARITY);

    expect(parsed.session.matched_count).toBe(0);
    expect(parsed.session.match_coverage_pct).toBeNull();
    expect(parsed.strategy.matched_count).toBe(41);
    expect(parsed.strategy.sample_sd_net).toHaveLength(51);
  });

  // BL-548 — 오버플로 회귀 픽스처도 같은 계약 위에 있어야 한다. 그리고 이 픽스처가
  // **실측 픽스처와 실제로 다른** 자리에서 다른지 못 박는다 — 같으면 판별력이 0 이다.
  it("긴 원장 Decimal 픽스처가 스키마를 통과하고 sub 전용 네 필드에서만 갈린다", () => {
    const parsed = OutcomeParityResponseSchema.parse(MOCK_OUTCOME_PARITY_LONG_LEDGER_SUB);

    expect(parsed.strategy.undecomposed_net).toHaveLength(51);
    expect(parsed.strategy.expected_only_gross).toHaveLength(51);
    expect(parsed.strategy.actual_only_net).toHaveLength(51);
    expect(parsed.strategy.ledger_only_net).toHaveLength(51);

    // 실측 픽스처의 같은 자리는 짧다 — 그래서 그 위에서는 이 결함이 안 보인다.
    const baseline = OutcomeParityResponseSchema.parse(MOCK_OUTCOME_PARITY);
    expect(baseline.strategy.undecomposed_net).toBe("0");
    expect(baseline.strategy.expected_only_gross).toBe("20");
  });
});
