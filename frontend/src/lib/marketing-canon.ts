// 마케팅 화면 공동 원장 — 거래소 지원표·성능 3값·로드맵 고지 SSOT (_KIT.md §4.1/§4.8).
// screen-14(랜딩)·screen-16(요금제)·screen-17(웨이트리스트)가 셀 단위로 같은 값을 렌더한다.
// 값을 여기 한 곳에만 두어 화면마다 지어내는 것(LESSON-063 크로스페이지 우회)을 막는다.

/** 거래소 지원 현황 1행. 로드맵 행은 환경·확인 범위를 무데이터(`—`)로 두고 title 로 이유를 밝힌다. */
export interface ExchangeSupportRow {
  exchange: string;
  /** null = 로드맵 행(무데이터 셀). */
  environment: string | null;
  status: "supported" | "roadmap";
  /** null = 로드맵 행(무데이터 셀). */
  scope: string | null;
}

/** 무데이터 표기 관례 (EMPTY_CELL 단독 셀 = "데이터 없음"). */
export const EMPTY_CELL = "—";

/** 로드맵 무데이터 사유 (terminology-ssot §1-D · 화면 간 바이트 동일). */
export const EXCHANGE_NO_ENV_TITLE = "연결 작업을 시작하지 않아 환경을 정하지 않았습니다.";
export const EXCHANGE_NO_SCOPE_TITLE = "연결 코드가 없어 확인한 범위가 없습니다.";

/** 표 caption (_KIT.md §4.8). */
export const EXCHANGE_TABLE_CAPTION = "로드맵 행은 연결 코드가 없어 빈 값으로 둡니다.";

/**
 * 거래소 지원 5행 (_KIT.md §4.8 마케팅 상한). Bybit 데모·메인넷만 지원, 나머지는 로드맵.
 * 상태 라벨 = 지원(chip done) / 로드맵(chip). OKX 를 "연결해 본" 목록에 넣지 않는다.
 */
export const EXCHANGE_SUPPORT: readonly ExchangeSupportRow[] = [
  { exchange: "Bybit", environment: "데모", status: "supported", scope: "주문 · 포지션 · TP/SL" },
  { exchange: "Bybit", environment: "메인넷", status: "supported", scope: "주문 · 포지션 · TP/SL" },
  { exchange: "OKX", environment: null, status: "roadmap", scope: null },
  { exchange: "Binance", environment: null, status: "roadmap", scope: null },
  { exchange: "Bitget", environment: null, status: "roadmap", scope: null },
];

/** 로드맵 3문장 고지 (_KIT.md §4.8 · screen-14 .sup-note 와 screen-17 .disclaimer 가 같은 문자열). */
export const ROADMAP_DISCLAIMER =
  "표에 없는 거래소는 지원하지 않습니다. 로드맵은 순서를 정해 두었다는 뜻이고, 착수일이나 완료일을 약속하는 말이 아닙니다. 날짜를 정하면 이 표에 그대로 적겠습니다.";

/** 성능 3값 — 조건과 함께만 쓴다 (_KIT.md §4.8). 조건 없는 속도 형용사 금지. */
export interface PerfFigure {
  value: string;
  note: string;
}

export const PERF_FIGURES: readonly PerfFigure[] = [
  {
    value: "20,064",
    note: "BTC/USDT 1h 봉 수. 2024-01-01 ~ 2026-04-14, 836일 구간입니다.",
  },
  {
    value: "3.24초",
    note: "run_2f9c41 백테스트 1회 소요 시간입니다. 로컬 실행 기준입니다.",
  },
  {
    value: "6,193",
    note: "초당 처리한 봉 수. 20,064 를 3.24 로 나눈 값을 반올림했습니다.",
  },
];

/** 성능 카드 하단 조건 (_KIT.md §4.8). */
export const PERF_DISCLAIMER =
  "로컬 개발 환경에서 한 번 측정한 결과입니다. 다른 환경의 속도는 측정하지 않았고 보장하지도 않습니다.";
