// 백테스트 도메인 화면 표기 SSOT — 실행 상태·거래 방향·지표 이름·표 헤더.
// 프로토타입 원장은 screen-03-backtests-list.html(실행 원장) 과 screen-04-trade-detail.html(거래) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type {
  BacktestStatus,
  StressTestHeadlineMetricKey,
  StressTestKind,
  StressTestStatus,
  TradeDirection,
  TradeStatus,
} from "./schemas";

/**
 * 실행 상태. queued/running/completed/failed 4종은 프로토타입 실측값이고
 * cancelling/cancelled 2종은 화면에 없어 코드 enum 을 덮기 위한 확장분이다.
 * screen-03-backtests-list.html:1215-1221 (aria-label="상태 필터" 셀렉트,
 * 옵션 5개 = 상태 전체 + 완료 + 실행 중 + 실패 + 대기)
 */
export const BACKTEST_STATUS_LABEL: Record<
  BacktestStatus,
  StatusLabelWithIcon
> = {
  queued: { label: "대기", tone: "neutral" },
  running: { label: "실행 중", tone: "accent" },
  completed: { label: "완료", tone: "done", showCheckIcon: true },
  failed: { label: "실패", tone: "warn" },
  cancelling: { label: "취소 중", tone: "neutral" }, // 프로토타입 미측정 · 확장분
  cancelled: { label: "취소", tone: "neutral" }, // 프로토타입 미측정 · 확장분
};

/** 상태 필터 탭. 라벨은 배지와 같은 문자열을 쓴다. */
export type BacktestStatusFilter = "all" | BacktestStatus;
export const BACKTEST_STATUS_FILTER_LABEL: Record<
  BacktestStatusFilter,
  string
> = {
  all: "전체",
  queued: "대기",
  running: "실행 중",
  cancelling: "취소 중",
  completed: "완료",
  failed: "실패",
  cancelled: "취소",
};

/** 거래 방향. screen-04-trade-detail.html:1234-1235 */
export const TRADE_DIRECTION_LABEL: Record<TradeDirection, string> = {
  long: "롱",
  short: "숏",
};

/** 거래 상태. 프로토타입 미측정 · 확장분 ("보유 중" 만 screen-01 에 있고 "청산됨" 은 17벌 0건). */
export const TRADE_STATUS_LABEL: Record<TradeStatus, string> = {
  open: "보유 중",
  closed: "청산됨",
};

/**
 * 청산 사유. `exit_kind` 가 없으면 시그널 청산이다 — 그 폴백까지가 계약이므로
 * `exitReasonLabel` 을 거치고 맵을 직접 인덱싱하지 않는다.
 *
 * 리포트 §04 미리보기에만 있던 것을 공용으로 올렸다. 전체 원장 페이지
 * (`/backtests/[id]/trades`)에는 이 열 자체가 없어서, 미리보기 상한(최신 25건)
 * 밖에서 일어난 강제청산은 화면 어디에도 안 보였다.
 */
export const EXIT_REASON_LABEL: Record<string, string> = {
  take_profit: "익절",
  stop_loss: "손절",
  trailing_stop: "추적 손절",
  liquidation: "강제청산",
};

/** 청산된 거래의 사유 라벨. 미청산(`exit_time` 없음)은 호출부가 판단한다. */
export function exitReasonLabel(exitKind: string | null | undefined): string {
  return (exitKind != null ? EXIT_REASON_LABEL[exitKind] : undefined) ?? "시그널 청산";
}

/**
 * 성과 지표 이름. 완전형만 화면 텍스트로 쓰고 축약은 th 의 abbr 속성에만 넣는다.
 * total_return 계열 3종은 서로 다른 enum 이므로 합치지 않는다.
 */
export const METRIC_LABEL = {
  totalReturn: "총 수익률",
  maxDrawdown: "최대 낙폭",
  sharpeRatio: "샤프 지수",
  sortinoRatio: "소르티노 지수", // 프로토타입 미측정 · 확장분 (17벌 0건)
  calmarRatio: "칼마 지수", // 프로토타입 미측정 · 확장분 (17벌 0건)
  winRate: "승률", // screen-04-trade-detail.html · screen-12-onboarding.html
  profitLossRatio: "손익비", // screen-04-trade-detail.html
  profitFactor: "수익 팩터", // screen-04-trade-detail.html
  numTrades: "거래 수",
  avgHoldingTime: "평균 보유", // screen-04-trade-detail.html
  /** 미결제 포지션의 진입가 대비 등락률. screen-01-trading-cockpit.html:1228 */
  positionUnrealizedReturn: "수익률",
  /** 거래 1건의 비용 차감 후 수익률. screen-04-trade-detail.html:1407 · 검산 :1411 */
  tradeRealizedReturn: "실현 수익률",
  /** 거래 1건의 비용 제외 총변동률. screen-04-trade-detail.html:1258 */
  tradeGrossReturn: "변동률",
  /** 전략의 가장 최근 완료 백테스트 1건 기준 수익률. screen-06-strategies-list.html:1246 */
  strategyLastRunReturn: "최근 수익률",
} as const;

export const METRIC_ABBR = {
  totalReturn: "수익률",
  maxDrawdown: "MDD",
  sharpeRatio: "샤프",
} as const;

/**
 * 실행 목록 표 헤더 11열. screen-03-backtests-list.html:1291-1326.
 * 주의 넷. 심볼과 주기는 별도 열이 아니라 "심볼 · 주기" 단일 th 다(:1293).
 * 시각 열 이름은 "생성 시각" 이 아니라 "실행 시각" 이다(:1320-1325).
 * 수익률·MDD·샤프 3열은 정렬 button 안의 시각 텍스트가 축약형이고
 * 완전형은 button 의 aria-label 에 있다. 두 값을 따로 들고 간다.
 * 액션 열이 있다(:1326).
 */
export const BACKTEST_LIST_HEADER = {
  runId: "실행 ID",
  strategy: "전략",
  symbolTimeframe: "심볼 · 주기",
  period: "기간",
  totalReturn: "수익률",
  maxDrawdown: "MDD",
  sharpeRatio: "샤프",
  numTrades: "거래 수",
  status: "상태",
  startedAt: "실행 시각",
  action: "액션",
} as const;

/**
 * 정렬 button 의 접근성 이름. 시각 텍스트가 축약형인 열만 갖는다.
 * screen-03-backtests-list.html:1296 / :1302 / :1308 / :1314 / :1321
 */
export const BACKTEST_LIST_SORT_LABEL = {
  totalReturn: "수익률 기준 정렬",
  maxDrawdown: "최대 낙폭 기준 정렬",
  sharpeRatio: "샤프 지수 기준 정렬",
  numTrades: "거래 수 기준 정렬",
  startedAt: "실행 시각 기준 정렬, 현재 내림차순으로 최근 실행이 위에 옵니다",
} as const;

/** 무데이터 사유. screen-03-backtests-list.html:1350 / :1357 / :1369 / :1417 / :1424 */
export const BACKTEST_EMPTY_REASON = {
  queuedNotStarted: "아직 실행이 시작되지 않았습니다.",
  queuedNoQueuePosition:
    "시작 시각이 아직 없습니다. 대기열 순번은 서버가 보고하지 않습니다.",
  runningNotFinished: "실행이 끝나야 계산됩니다.",
  failedDataCollection:
    "Bybit OHLCV 수집이 중단되어 실행이 완료되지 않았습니다.",
  failedStageNote: "데이터 수집 단계에서 중단",
} as const;

/** 신규 실행 화면명. 진입 버튼 라벨이 정본이고 h1 만 동사형을 유지한다. */
export const NEW_BACKTEST_LABEL = {
  entry: "새 백테스트",
  heading: "새 백테스트 실행",
} as const;

/**
 * [BL-414] 스트레스 테스트 종류 4종. 실행 버튼 라벨은 영문 고유명(Monte Carlo 등)을
 * 쓰지만 이력 표는 한국어 열이라 여기서 한 번 한국어로 고정한다.
 */
export const STRESS_TEST_KIND_LABEL: Record<StressTestKind, string> = {
  monte_carlo: "몬테카를로",
  walk_forward: "워크포워드",
  cost_assumption_sensitivity: "비용 가정 민감도",
  param_stability: "파라미터 안정성",
};

/** 스트레스 테스트 실행 상태. 백테스트와 달리 취소가 없어 4종뿐이다. */
export const STRESS_TEST_STATUS_LABEL: Record<
  StressTestStatus,
  StatusLabelWithIcon
> = {
  queued: { label: "대기", tone: "neutral" },
  running: { label: "실행 중", tone: "accent" },
  completed: { label: "완료", tone: "done", showCheckIcon: true },
  failed: { label: "실패", tone: "warn" },
};

/** 이력 표의 대표 지표 이름. BE 가 보내는 키를 화면 표기로 옮긴다. */
export const STRESS_TEST_HEADLINE_METRIC_LABEL: Record<
  StressTestHeadlineMetricKey,
  string
> = {
  max_drawdown_p95: METRIC_ABBR.maxDrawdown + " p95",
  degradation_ratio: "열화 비율",
  worst_cell_sharpe: "최저 " + METRIC_ABBR.sharpeRatio,
};

/**
 * 이력 표 헤더.
 * ★키에 `Column` 접미사를 붙인 이유 — `no-raw-enum-labels` 가드는 JSX 자식 위치의
 * 멤버체인 **마지막 세그먼트**로 판정한다. 키가 `kind`/`status` 면 헤더 문자열을
 * 그리는 `{HEADER.kind}` 가 원시 enum 렌더로 잡힌다(실측). 가드를 넓히는 대신 이름을 비켰다.
 */
export const STRESS_TEST_HISTORY_HEADER = {
  kindColumn: "종류",
  statusColumn: "상태",
  metricColumn: "대표 지표",
  createdAtColumn: "실행 시각",
  actionColumn: "액션",
} as const;

/** 이력 표의 무데이터·안내 문구. */
export const STRESS_TEST_HISTORY_LABEL = {
  caption: "스트레스 테스트 이력",
  empty: "이 백테스트에는 아직 실행한 스트레스 테스트가 없습니다.",
  loading: "이력을 불러오는 중…",
  loadFailed: "이력을 불러오지 못했습니다.",
  select: "이 실행 결과 보기",
  selected: "지금 보고 있는 실행",
  /** `degradation_ratio` 가 `"Infinity"` 인 경우. 무데이터(—)와 구분해야 한다. */
  infinity: "∞",
} as const;

/**
 * [BL-414] 표가 1페이지 상한에서 잘렸을 때의 고지. ★조용히 자르지 않는다 —
 * 「이력 전체」라 적어 놓고 21번째 실행이 화면에서 사라지면 그것이 거짓말이다
 * (codex 적대 리뷰 P1, 2026-08-17).
 */
export function stressTestHistoryTruncatedLabel(shown: number, total: number): string {
  return `최근 ${shown}건만 표시합니다 (전체 ${total}건).`;
}
