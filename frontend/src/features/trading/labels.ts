// 트레이딩 도메인 화면 표기 SSOT — 주문 상태·주문 방향·포지션 방향·실행 경로·표 헤더.
// 프로토타입 원장은 screen-11-orders.html(주문) 과 screen-01-trading-cockpit.html(포지션) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type { Order } from "./schemas";

export type OrderState = Order["state"];
export type OrderSide = Order["side"];

/** 주문 상태 5종. screen-11-orders.html:1290/1304/1346/1360/1374 */
export const ORDER_STATE_LABEL: Record<OrderState, StatusLabelWithIcon> = {
  pending: { label: "대기", tone: "neutral" },
  submitted: { label: "전송", tone: "neutral" },
  filled: { label: "체결", tone: "done", showCheckIcon: true },
  cancelled: { label: "취소", tone: "neutral" },
  rejected: { label: "거부", tone: "warn" },
};

/**
 * 주문 방향. 포지션의 롱·숏과는 다른 값이라 배지 클래스도 분리한다
 * (.order-side.buy/.sell vs .side.long/.short). screen-11-orders.html:1271
 */
export const ORDER_SIDE_LABEL: Record<OrderSide, string> = {
  buy: "매수",
  sell: "매도",
};

/** 포지션 방향. screen-01-trading-cockpit.html:1238 · screen-04-trade-detail.html:1265 */
export type PositionSide = "long" | "short";
export const POSITION_SIDE_LABEL: Record<PositionSide, string> = {
  long: "롱",
  short: "숏",
};

/**
 * 실행 경로 3단. 서로 직교하는 축이므로 하나로 합치지 않는다.
 * mock = 로컬 목 어댑터 / demo = Bybit 데모 계정 / live = 실자금.
 */
export type ExecutionMode = "mock" | "demo" | "live";
export const EXECUTION_MODE_LABEL: Record<ExecutionMode, string> = {
  mock: "모의",
  demo: "데모",
  live: "라이브",
};
/** screen-11-orders.html:1404 title · screen-01-trading-cockpit.html:1553 · screen-16-pricing.html:1487 */
export const EXECUTION_MODE_HINT: Record<ExecutionMode, string> = {
  mock: "거래소를 붙이지 않고 로컬 목 어댑터로 실행한 주문입니다. 실제 거래소에는 나가지 않았습니다.",
  demo: "데모는 실거래와 같은 코드 경로를 쓰지만 슬리피지와 체결 지연은 다르게 나타납니다.",
  live: "라이브 주문은 실제 자금을 움직이고 손실은 사용자 책임입니다.",
};

/** 주문번호 출처 배지. screen-11-orders.html:1306(브로커) · :1404(모의) */
export type OrderIdSource = "broker" | "mock";
export const ORDER_ID_SOURCE_LABEL: Record<OrderIdSource, string> = {
  broker: "브로커",
  mock: "모의",
};

/**
 * 주문 표 헤더 10열. screen-11-orders.html:1269-1278 의 th 를 순서대로 옮긴 것이고
 * 문자열은 화면이 인쇄하는 값과 바이트 일치한다.
 * 주의 둘. createdAt 은 "시간" 이 아니라 "시각" 이다.
 * takeProfitStopLoss 는 가운뎃점 앞뒤에 공백이 없다("익절·손절").
 */
export const ORDER_TABLE_HEADER = {
  createdAt: "시각",
  symbol: "심볼",
  side: "주문 방향",
  quantity: "수량",
  filledPrice: "체결가",
  state: "상태",
  takeProfitStopLoss: "익절·손절",
  brokerOrderId: "거래소 주문번호",
  errorMessage: "오류",
  action: "액션",
} as const;

/** 주문 방향 열 헤더 title. 롱·숏과의 혼동을 막는 문구다. */
export const ORDER_SIDE_HEADER_HINT =
  "주문의 매수·매도 방향입니다. 포지션의 롱·숏 방향과는 다른 값이라 트레이딩 코크핏의 롱·숏 배지와 구분해 표시합니다.";

/** 부가 플래그 배지. screen-11-orders.html:1287 */
export const ORDER_FLAG_LABEL = {
  reduceOnly: "감소전용",
} as const;
export const ORDER_FLAG_HINT = {
  reduceOnly:
    "열려 있는 포지션을 줄이는 주문입니다. 새 포지션을 만들지 않습니다.",
} as const;

/**
 * 상태 필터 탭. 라벨 단위(5종)와 필터 단위(4종)의 입도가 다르다.
 * 화면은 라벨 뒤에 건수를 붙여 인쇄한다(전체 14 / 체결 5 / 대기·전송 7 / 취소·거부 2).
 * 건수는 데이터에서 파생되므로 라벨만 여기 둔다. screen-11-orders.html:1219-1222
 */
export type OrderStateFilter = "all" | "filled" | "open" | "closed";
export const ORDER_STATE_FILTER_LABEL: Record<OrderStateFilter, string> = {
  all: "전체",
  filled: "체결",
  open: "대기·전송",
  closed: "취소·거부",
};

/** 무데이터 사유. screen-11-orders.html:1289 · :1292 · :1347 · :1348 */
export const ORDER_EMPTY_REASON = {
  filledPriceNotYet: "아직 체결되지 않아 체결가가 없습니다.",
  brokerIdNotSent: "아직 거래소로 보내지 않아 주문번호가 없습니다.",
  brokerIdRejected: "거래소로 나가기 전에 걸러져서 주문번호가 없습니다.",
  takeProfitStopLossRejected:
    "거래소로 나가기 전에 걸러져서 익절과 손절도 붙지 않았습니다.",
} as const;

/**
 * 청산가는 주문 표에 두지 않는다. 체결된 주문이 곧 열린 포지션을 뜻하지 않고
 * 포지션 API 도 없기 때문이다. 포지션 화면으로 위임한다.
 * 원문 4문장 그대로다. screen-11-orders.html:1479
 */
export const ORDER_LIQUIDATION_DELEGATION_NOTE =
  "청산가는 이 표에 표시하지 않습니다. 체결된 주문이 곧 열린 포지션을 뜻하지 않고(이미 청산됐을 수 있습니다), 지금 포지션을 돌려주는 API 도 아직 없기 때문입니다. 확인할 수 없는 값을 라이브 위험처럼 보이게 하지 않으려고 칸 자체를 두지 않았습니다. 포지션은 트레이딩 코크핏에서 확인하세요.";

/** 킬 스위치. 기능명과 버튼 라벨(동사형)을 분리한다. screen-01-trading-cockpit.html:1336 · :1154 · :1157 */
export const KILL_SWITCH_LABEL = {
  feature: "킬 스위치",
  action: "긴급 정지",
  confirm:
    "긴급 정지는 모든 포지션 시장가 청산 후 세션 중지. 되돌릴 수 없습니다.",
} as const;

/** 세션 빈 상태. screen-11-orders.html:1572-1573 (카드 제목 :1563 "라이브 세션 주문") */
export const ORDER_EMPTY_STATE = {
  headline: "표시할 주문이 없습니다.",
  description: "라이브·데모 세션이 주문을 실행하면 이곳 원장에 기록됩니다.",
} as const;
