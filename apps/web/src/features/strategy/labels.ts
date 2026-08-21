// 전략 도메인 화면 표기 SSOT — Pine 파싱 상태·전략 수명주기 상태·정책 문구.
// 프로토타입 원장은 screen-06-strategies-list.html(목록 12행) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type { ParsePreviewResponse } from "./schemas";

export type ParseStatus = ParsePreviewResponse["status"];

/**
 * Pine 파싱 미리보기 결과. 지금 코드에는 같은 Record 가 두 파일에 복제돼 있고
 * ok 값이 "변환 완료"(new) 와 "변환 가능"(edit) 으로 갈렸다.
 * 미리보기 단계에서는 아직 아무것도 변환되지 않았으므로 "변환 가능" 이 정확하다.
 * **근거는 실 코드이고 프로토타입 근거는 없다.** 세 라벨 모두 17벌에 0건이므로
 * 이 Record 만은 화면 실측이 아니라 코드 간 중복 해소 판정이다.
 */
export const PARSE_STATUS_LABEL: Record<ParseStatus, StatusLabelWithIcon> = {
  ok: { label: "변환 가능", tone: "done", showCheckIcon: true },
  unsupported: { label: "일부 미지원", tone: "warn" },
  error: { label: "오류", tone: "warn" },
};

/**
 * 파싱 상태 필터 탭. 라벨은 배지(PARSE_STATUS_LABEL)와 같은 문자열을 쓴다.
 * 수명주기 칩과 별개로 실존 필드 parse_status 를 필터 축으로 쓴다. API 가
 * parse_status 쿼리를 지원한다(features/strategy/api.ts listStrategies).
 */
export type ParseStatusFilter = "all" | ParseStatus;
export const PARSE_STATUS_FILTER_LABEL: Record<ParseStatusFilter, string> = {
  all: "전체",
  ok: "변환 가능",
  unsupported: "일부 미지원",
  error: "오류",
};

/**
 * 전략 수명주기 상태. 백엔드 파생 필드와 프론트 스키마가 같은 enum 값을 사용한다.
 * screen-06-strategies-list.html:1260(배포됨) · :1281(검증됨) · :1302(초안)
 */
export type StrategyLifecycle = "draft" | "validated" | "deployed";
export const STRATEGY_LIFECYCLE_LABEL: Record<StrategyLifecycle, StatusLabelWithIcon> = {
  draft: { label: "초안", tone: "neutral" },
  validated: { label: "검증됨", tone: "done" }, // 체크 아이콘 없음 (screen-06 6건 전부)
  deployed: { label: "배포됨", tone: "accent" },
};

/**
 * 전략 목록 표 헤더 10열. screen-06-strategies-list.html:1242-1251.
 * 주의 넷. 첫 열은 "전략" 이 아니라 "전략명" 이다.
 * 심볼과 주기는 별도 열이 아니라 "심볼 · 주기" 단일 th 다(:1244).
 * MDD·샤프 2열은 시각 텍스트가 축약형이고 완전형은 th 의 aria-label 에 있다.
 * 상태 열(:1243)과 액션 열(:1251)이 있다.
 */
export const STRATEGY_LIST_HEADER = {
  name: "전략명",
  status: "상태",
  symbolTimeframe: "심볼 · 주기",
  paramCount: "파라미터",
  lastRunReturn: "최근 수익률",
  maxDrawdown: "MDD",
  sharpeRatio: "샤프",
  backtestCount: "백테스트",
  updatedAt: "마지막 수정",
  action: "액션",
} as const;

/**
 * 축약 th 의 접근 가능한 이름. screen-06 은 정렬 컨트롤이 없는 정적 th 라
 * screen-03 처럼 "... 기준 정렬" 을 쓰지 않고 확정 용어만 넣는다.
 * screen-06-strategies-list.html:1247 · :1248
 */
export const STRATEGY_LIST_HEADER_ARIA = {
  maxDrawdown: "최대 낙폭",
  sharpeRatio: "샤프 지수",
} as const;

/**
 * 백테스트 카운트 열의 정의를 반드시 명시한다.
 * 화면이 열 이름을 "백테스트" 로만 인쇄해 완료 기준인지 전체 실행 기준인지
 * 프로토타입만으로는 확정할 수 없었다 (screen-06-strategies-list.html:1249).
 */
export const STRATEGY_BACKTEST_COUNT_HINT =
  "완료된 백테스트 수입니다. 실행 중이거나 실패한 실행은 세지 않습니다.";

/** 무데이터 사유. screen-06-strategies-list.html:1305-1307 (06 에서 4행 x 3칸 = 12셀) */
export const STRATEGY_EMPTY_REASON = {
  noBacktestYet: "아직 백테스트를 실행하지 않았습니다.",
} as const;

/** ADR-003 전체 미지원 정책. 화면마다 갈린 어휘를 하나로 잠근다. */
export const UNSUPPORTED_POLICY_NOTE =
  "미지원 함수가 하나라도 있으면 부분 실행 없이 전체를 지원되지 않음으로 처리합니다. 잘못된 결과를 내는 것보다 낫습니다.";

/** 엔진 표기. ADR-011 상 "벡터화" 표기는 금지다. */
export const ENGINE_LABEL = "pine_v2 · 바 단위 이벤트 루프";
