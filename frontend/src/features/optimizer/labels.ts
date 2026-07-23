// 옵티마이저 도메인 화면 표기 SSOT — 방식·상태·목표 지표·방향·파라미터 필드·표 헤더.
// 프로토타입 원장은 screen-09-optimizer-list.html(목록) 과 screen-10-optimizer-detail.html(상세) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type {
  BayesianPrior,
  OptimizationDirection,
  OptimizationKind,
  OptimizationObjectiveMetric,
  OptimizationStatus,
} from "./schemas";

/**
 * 도메인명은 역할로 나뉜다.
 * page   = 사이드바 · title · breadcrumb · h1 · 푸터 5축 (screen-09-optimizer-list.html:1563)
 * action = 동사 · 실행 유형 (screen-09-optimizer-list.html:1179 "최적화 제출")
 */
export const OPTIMIZER_DOMAIN_LABEL = {
  page: "옵티마이저",
  action: "최적화",
} as const;

/** 방식 3종. screen-09-optimizer-list.html:1200-1202 셀렉트 옵션 */
export const OPTIMIZATION_KIND_LABEL: Record<OptimizationKind, string> = {
  grid_search: "그리드 탐색",
  bayesian: "베이지안 탐색",
  genetic: "유전 알고리즘",
};

/** 실행 상태 4종. screen-09-optimizer-list.html:1296/1310/1323/1346 */
export const OPTIMIZATION_STATUS_LABEL: Record<
  OptimizationStatus,
  StatusLabelWithIcon
> = {
  queued: { label: "대기", tone: "neutral" },
  running: { label: "실행 중", tone: "accent" },
  completed: { label: "완료", tone: "done", showCheckIcon: true },
  failed: { label: "실패", tone: "warn" },
};

/** 목표 지표 3종 완전형. screen-09-optimizer-list.html:1209-1211 셀렉트 옵션 */
export const OBJECTIVE_METRIC_LABEL: Record<
  OptimizationObjectiveMetric,
  string
> = {
  sharpe_ratio: "샤프 지수",
  total_return: "총 수익률",
  max_drawdown: "최대 낙폭",
};

// 목표 지표 축약 매핑(`OBJECTIVE_METRIC_ABBR`)은 두지 않는다. `_KIT.md` §4.10 이
// 캐논이며, 축약은 지표별 상수가 아니라 **자리**로 판정한다 — 좁은 칸이면 축약,
// 표 헤더·산문이면 완전형이다. 축약해도 되는 이름은 `MDD` 와 `샤프` 둘뿐이고
// `수익률` 은 명시적으로 금지다. 3-키 Record 는 그 판정을 지표 단위로 잘못
// 인코딩해서 `수익률` 축약을 되살린다. 축약이 필요한 좁은 칸은 해당 컴포넌트에서
// 리터럴로 쓰고, 접근 이름에는 위 완전형을 단다(가시 텍스트로 열 폭을 흔들지 않는다).

/** 최적화 방향. screen-09-optimizer-list.html:1218-1219 */
export const OBJECTIVE_DIRECTION_LABEL: Record<OptimizationDirection, string> =
  {
    maximize: "최대화",
    minimize: "최소화",
  };
export const OBJECTIVE_DIRECTION_HINT: Record<OptimizationDirection, string> = {
  maximize: "큰 값이 좋음",
  minimize: "작은 값이 좋음",
};

/**
 * 파라미터 공간 필드 종류. 원시 kind 문자열을 그대로 인쇄하지 않는다.
 * **프로토타입 미측정 · 확장분.** 네 라벨 모두 17벌에 0건이며 코드 노출을 막기 위해 새로 지었다.
 */
export type ParamFieldKind = "integer" | "decimal" | "categorical" | "bayesian";
export const PARAM_FIELD_KIND_LABEL: Record<ParamFieldKind, string> = {
  integer: "정수 구간",
  decimal: "실수 구간",
  categorical: "범주 목록",
  bayesian: "연속 구간",
};

/** 베이지안 사전분포. **프로토타입 미측정 · 확장분** (세 라벨 모두 17벌에 0건). */
export const BAYESIAN_PRIOR_LABEL: Record<BayesianPrior, string> = {
  uniform: "균등",
  log_uniform: "로그 균등",
  normal: "정규",
};

/** 베이지안 반복 단계. screen-10 에는 인쇄되지 않았고 코드 노출을 막기 위한 확장분이다. */
export type BayesianPhase = "random" | "acquisition";
export const BAYESIAN_PHASE_LABEL: Record<BayesianPhase, string> = {
  random: "초기 랜덤",
  acquisition: "획득 함수",
};

/** 실행 목록 표 헤더 8열. screen-09-optimizer-list.html:1277-1284 · 화면 문자열과 바이트 일치 */
export const OPTIMIZER_LIST_HEADER = {
  runId: "실행 ID",
  kind: "방식",
  backtest: "대상 백테스트",
  objective: "목표 지표",
  bestObjective: "최고 목표값",
  status: "상태",
  createdAt: "생성 시각",
  action: "액션",
} as const;

/**
 * 셀 리더보드 표 헤더 8열. screen-10-optimizer-detail.html:1320-1327.
 * 주의 셋. 첫 열은 "순위" 가 아니라 "표시 순서" 다. 정렬을 바꿔도 목표 함수와
 * "최적" 표시는 고정이라는 사실(:1427)과 맞추려고 화면이 고른 말이다.
 * 파라미터는 단일 "파라미터" 열이 아니라 fastLength · slowLength 2열로 분리돼 있다.
 * 목표값 전용 열은 없다. 목표 함수인 샤프 지수 열이 그 역할을 겸한다.
 * 이 표는 이 실행의 파라미터 이름을 그대로 인쇄하므로 열 구성이 실행마다 달라진다.
 * 그래서 아래 두 키는 이 프로토타입 실행(MA Crossover 그리드 탐색)의 실측값이고,
 * 이식할 때는 param_space 의 필드 이름에서 만들어야 한다.
 */
export const OPTIMIZER_CELL_HEADER = {
  displayOrder: "표시 순서",
  paramFast: "fastLength",
  paramSlow: "slowLength",
  sharpe: "샤프 지수",
  totalReturn: "총 수익률",
  maxDrawdown: "최대 낙폭",
  numTrades: "거래 수",
  action: "액션",
} as const;

/**
 * 무데이터 사유. 상태별로 문구가 다르다.
 * screen-09-optimizer-list.html:1297 / :1308 / :1344 · screen-10-optimizer-detail.html:1415 / :1412
 */
export const OPTIMIZER_EMPTY_REASON = {
  queuedNotStarted: "아직 실행이 시작되지 않아 평가 결과가 없습니다.",
  queuedNoQueuePosition:
    "시작 시각이 아직 없습니다. 대기열 순번은 서버가 보고하지 않습니다.",
  runningNoIntermediate:
    "실행이 끝나야 결과가 저장됩니다. 서버는 중간 최고값을 보고하지 않습니다.",
  failedInvalidRange:
    "파라미터 공간의 하한이 상한보다 커서 탐색 범위를 만들지 못했고, 평가가 한 번도 실행되지 않았습니다.",
  degenerateNoSharpe: "거래가 0건이라 샤프 지수를 계산할 표본이 없습니다.",
  degenerateNoRank: "거래가 0건이라 순위를 매길 근거가 없습니다.",
  noEtaByDesign:
    "실행 중 작업의 남은 시간은 표시하지 않습니다. 서버가 진행 회차를 아직 보고하지 않기 때문입니다.",
  noProgressMeter:
    "최적화는 서버가 진행률을 보고하지 않아 미터를 그리지 않습니다.",
} as const;

/**
 * 빈 상태. screen-09 가 실제로 그리는 빈 상태는 "실행 이력 없음" 이 아니라
 * "보관함 비어 있음" 하나뿐이다. screen-09-optimizer-list.html:1484-1485
 */
export const OPTIMIZER_ARCHIVE_EMPTY_STATE = {
  headline: "보관한 실행이 없습니다.",
  description:
    "끝난 실행을 보관해 두면 목록에서 빠지고, 결과는 그대로 남습니다.",
} as const;

/** 목록 로드 실패. screen-09-optimizer-list.html:1460-1461 */
export const OPTIMIZER_LIST_ERROR_STATE = {
  headline: "목록을 다시 불러오지 못했습니다.",
  description:
    "위 표는 마지막으로 성공한 응답입니다. 그 뒤로 갱신되지 않았습니다.",
} as const;

/** 대상 백테스트 선택 제약. screen-09-optimizer-list.html:1235 · 원문 3문장 그대로다 */
export const OPTIMIZER_BACKTEST_PICKER_NOTE =
  "목록에는 완료된 백테스트만 나옵니다. 실행 중이거나 실패한 백테스트는 최적화의 기준이 될 수 없습니다. 최대 낙폭을 목표로 고르면 방향은 최소화가 기본값입니다.";

/** 방식별 상한. screen-09-optimizer-list.html:1231 · 원문 2문장 그대로다 */
export const OPTIMIZER_LIMIT_NOTE =
  "지금 고른 그리드 탐색은 조합 수가 9개를 넘으면 제출이 거부됩니다. 베이지안 탐색과 유전 알고리즘은 조합 대신 평가 횟수로 끊으며 상한은 100회입니다.";
