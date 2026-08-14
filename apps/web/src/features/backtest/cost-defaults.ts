// 백테스트 비용 가정 기본값 — FE 의 단일 정본 ([BL-730]).
/**
 * 수수료·슬리피지 기본값.
 *
 * ## 왜 이 파일이 있나
 *
 * 이 두 숫자가 FE 안에서만 **5벌**로 흩어져 있었고, [BL-603] 이 2026-08-07 에 값을 좁혔을 때
 * 3벌만 따라갔다. 남은 2벌(`features/backtest/schemas.ts` 의 zod default,
 * `onboarding/_components/step-3-backtest.tsx` 의 하드코딩 submit)이 낡은 채로
 * **왕복 0.30%** 를 제출했다 — 실측 왕복은 0.138% 다.
 *
 * 리터럴을 한 벌 더 만드는 것이 원인이었으므로, 고치는 방법도 「값을 또 베끼는 것」이 될 수
 * 없다. FE 의 모든 소비처는 이 모듈을 import 한다.
 *
 * ## BE 와의 관계
 *
 * **정본은 백엔드다** — `apps/api/src/backtest/engine/types.py`(엔진 기본값)와
 * `apps/api/src/backtest/schemas.py`(API Pydantic 기본값)가 그것이고, 그 둘은 서로를
 * 가리키는 주석을 갖고 있다. 여기 값은 그 미러이며 **화면에 미리 채워 보여주기 위한 것**이다.
 *
 * ★그래서 이 값이 낡아도 API 는 자기 기본값으로 정상 동작한다 — 대신 **사용자가 폼에서 본
 * 숫자와 실제로 적용된 숫자가 갈린다.** 온보딩처럼 값을 **명시적으로 실어 보내는** 경로에서는
 * 낡은 미러가 그대로 제출되므로 BE 기본값이 아예 안 쓰인다. [BL-730] 이 그 경로였다.
 *
 * BE 를 고칠 때 이 파일도 함께 고쳐라. 격자·프리셋을 만들 때는 **이 점을 반드시 포함**해라 —
 * 현재 기본값이 격자 밖에 있으면 사용자가 기본 설정을 재현할 수 없다([BL-698] 계열).
 */

/** taker 수수료 0.055% — Bybit demo 실측. BE `engine/types.py` `fees` 의 미러. */
export const DEFAULT_FEES_PCT = 0.00055;

/** 슬리피지 0.014% — taker market/stop 에만 적용(limit 제외). BE `slippage` 의 미러. */
export const DEFAULT_SLIPPAGE_PCT = 0.00014;
