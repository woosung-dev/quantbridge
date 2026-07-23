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
 * 주문번호 출처 배지 title. 모의는 실행 경로 힌트를 그대로 쓰고(로컬 목 어댑터라 거래소에
 * 나가지 않음), 브로커는 거래소가 돌려준 번호임을 밝힌다. 컴포넌트는 데모·라이브를 구분하지
 * 않으므로 특정 거래소명은 넣지 않는다. screen-11-orders.html:1306 · :1404
 */
export const ORDER_ID_SOURCE_HINT: Record<OrderIdSource, string> = {
  broker: "거래소가 돌려준 주문번호입니다.",
  mock: EXECUTION_MODE_HINT.mock,
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

/** 무데이터 사유. screen-11-orders.html:1289 · :1292 · :1347 · :1348 · :1373 · :1375 */
export const ORDER_EMPTY_REASON = {
  filledPriceNotYet: "아직 체결되지 않아 체결가가 없습니다.",
  filledPriceRejected: "거부된 주문이라 체결가가 없습니다.",
  filledPriceCancelled: "체결 전에 취소돼서 체결가가 없습니다.",
  brokerIdNotSent: "아직 거래소로 보내지 않아 주문번호가 없습니다.",
  brokerIdRejected: "거래소로 나가기 전에 걸러져서 주문번호가 없습니다.",
  takeProfitStopLossNone: "이 주문에는 익절도 손절도 걸려 있지 않습니다.",
  takeProfitStopLossRejected:
    "거래소로 나가기 전에 걸러져서 익절과 손절도 붙지 않았습니다.",
} as const;

/**
 * 체결가 무데이터 title 을 상태별로 고른다. 체결 전 상태(대기·전송)는 같은 문구를 쓴다.
 * screen-11-orders.html:1289(대기) · :1345(거부) · :1373(취소).
 */
export function filledPriceEmptyReason(state: OrderState): string {
  if (state === "rejected") return ORDER_EMPTY_REASON.filledPriceRejected;
  if (state === "cancelled") return ORDER_EMPTY_REASON.filledPriceCancelled;
  return ORDER_EMPTY_REASON.filledPriceNotYet;
}

/** 오류 없음 셀 title. 상태마다 왜 오류가 없는지 다르게 밝힌다. screen-11-orders.html:1293 · :1307 · :1363 · :1377 */
export const ORDER_ERROR_NONE_TITLE: Partial<Record<OrderState, string>> = {
  pending: "오류 없이 대기 중입니다.",
  submitted: "오류 없이 전송된 상태입니다.",
  filled: "오류 없이 체결됐습니다.",
  cancelled: "사용자가 직접 취소했습니다. 오류는 없습니다.",
};

export const ORDER_CANCEL_ACTION = {
  label: "주문 취소",
  title: {
    pending: "대기 중인 주문을 취소합니다. 취소하면 다시 살릴 수 없고 새로 내야 합니다.",
    submitted: "전송된 주문의 취소를 거래소에 요청합니다. 이미 체결됐다면 취소되지 않습니다.",
    filled: "이미 체결이 끝난 주문이라 취소할 수 없습니다.",
    cancelled: "이미 취소된 주문입니다.",
    rejected: "이미 거부로 끝난 주문이라 취소할 수 없습니다.",
  } satisfies Record<OrderState, string>,
} as const;

/** 추적손절 라벨. §4.6 규약 — 원시 "trail" 문자열 대신 한글 라벨을 쓴다. screen-11-orders.html:1333 */
export const ORDER_TRAILING_STOP_LABEL = "추적손절";

/** 추적손절 셀 title. screen-11-orders.html:1333 */
export const ORDER_TRAILING_STOP_TITLE =
  "체결가에서 벌어진 거리를 따라붙는 손절입니다.";

/**
 * 폴링 정책 안내. 주문 원장은 자기 리소스의 갱신 정책을 명시한다(§4.6).
 * 실제 훅은 진행 중 주문이 있으면 5초, 없으면 30초로 폴링한다(hooks.ts).
 */
export const ORDER_POLLING_NOTE =
  "이 목록은 30초 간격으로 다시 불러옵니다. 진행 중인 주문이 있으면 더 자주 확인합니다.";

/**
 * 상태 필터 안내 2줄. 첫 줄은 필터 대상 범위, 둘째 줄은 미체결 건수와 사이드바 배지의 일치를 밝힌다.
 */
export const ORDER_FILTER_HINT = {
  scope:
    "버튼을 누르면 원장 표에서 그 상태의 행만 남깁니다. 거르는 대상은 이미 받아온 주문이고, 아직 받아오지 않은 페이지는 걸러지지 않습니다.",
  navCount:
    "위 미체결 건수는 대기와 전송을 더한 값입니다. 사이드바 배지도 같은 미체결 주문 수를 표시합니다.",
} as const;

/**
 * 거래소 주문번호 안내. 뒤 8자만 보여 주고, 아직 번호가 없는 상태를 밝힌다.
 * 브로커·모의 구분 배지는 주문 스키마에 대응 필드가 없어 렌더하지 않는다(§4.9).
 */
export const ORDER_NUMBER_NOTE =
  "거래소 주문번호는 뒤 8자만 보여줍니다. 대기와 거부 상태에는 아직 번호가 없어서 빈 칸으로 둡니다.";

/** 목록 화면 섹션 카피(구조·라벨). screen-11-orders.html:1211-1213 · :1240-1242 · :1249 */
export const ORDER_LEDGER_COPY = {
  filterEyebrow: "상태 필터",
  filterTitle: "어떤 상태만 볼지 고르기",
  filterDesc:
    "아직 끝나지 않은 주문과 이미 끝난 주문을 나눠서 봅니다. 괄호 없이 붙은 숫자가 그 상태의 건수입니다.",
  listEyebrow: "목록",
  listDescription:
    "세션이 낸 주문을 낸 시각의 역순으로 쌓습니다. 값이 아직 없는 칸은 비어 있다고 그대로 표시합니다.",
  cardTitle: "주문 원장",
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
