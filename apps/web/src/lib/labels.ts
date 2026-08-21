// 화면 표기 SSOT 의 공용 원시 타입 — 칩 톤 토큰, 무데이터 표기, 미지 enum 폴백 헬퍼.

/**
 * 상태 배지 톤. 프로토타입 셸 클래스와 1:1 대응한다.
 * - neutral: 아직 결과가 없거나 사용자 행위로 끝난 상태
 * - done   : 값이 남은 완결 상태 (--bull)
 * - accent : 진행 중이거나 활성인 상태 (--copper)
 * - warn   : 실패 · 거부 · 미저장 (--warn)
 */
export type ChipTone = "neutral" | "done" | "accent" | "warn";

/**
 * 톤에서 프로토타입 셸 클래스로의 매핑.
 * React 에서는 이 표만 디자인 토큰(data-tone 등)으로 갈아끼우면 되고,
 * 라벨 모듈은 손대지 않는다.
 */
export const CHIP_TONE_CLASS: Record<ChipTone, string> = {
  neutral: "chip",
  done: "chip done",
  accent: "chip accent",
  warn: "chip warn",
};

/**
 * 값 없음을 뜻하는 셀 표기 (U+2014).
 * 문자열 리터럴로 직접 쓰지 말고 이 상수를 참조한다.
 * 프로토타입 규약상 이 문자가 단독으로 쓰인 셀만 "데이터 없음" 관례로 허용된다.
 */
export const EMPTY_CELL = "—";

/** 라벨 1개와 톤 1개. 상태 계열 enum 이 공통으로 쓰는 모양. */
export interface StatusLabel {
  readonly label: string;
  readonly tone: ChipTone;
}

/** 체크 아이콘을 붙이는 톤인지. done 이면서 완결 실행·주문일 때만 true 를 넘긴다. */
export interface StatusLabelWithIcon extends StatusLabel {
  readonly showCheckIcon?: boolean;
}

// BL-571 (c) — 이미 경고한 (scope, key) 쌍. 폴링 화면은 같은 미지 코드를 초당 여러 번 다시
// 렌더하므로, 덮지 않으면 /trading 에서 40초에 67건이 찍혀 정작 읽어야 할 다른 로그를 덮는다.
// 코드당 1회면 "서버가 새 enum 을 먼저 배포했다" 는 신호는 그대로 전달된다.
const warnedKeys = new Set<string>();

function warnUnknownKey(key: string, scope: string): void {
  if (process.env.NODE_ENV === "production") return;
  // scope 를 함께 묶는다 — 같은 코드라도 표가 다르면 다른 결함이다.
  const warned = `${scope}::${key}`;
  if (warnedKeys.has(warned)) return;
  warnedKeys.add(warned);
  // 서버가 새 enum 을 먼저 배포한 경우를 개발 중에 즉시 드러낸다.
  console.warn(`[labels] ${scope} 에 없는 enum 값입니다: ${key}`);
}

/**
 * 미지 enum 폴백 (문자열 라벨).
 * 표에 없는 값이 오면 원문을 그대로 돌려준다. 화면이 빈칸이 되거나
 * undefined 접근으로 터지는 것보다 낫고, 원시 enum 노출 자체가 버그 신호다.
 */
export function labelOf<K extends string>(
  table: Readonly<Record<K, string>>,
  key: string,
  scope = "labels",
): string {
  const hit = (table as Readonly<Record<string, string | undefined>>)[key];
  if (hit === undefined) {
    warnUnknownKey(key, scope);
    return key;
  }
  return hit;
}

/**
 * 미지 enum 폴백 (라벨 + 톤).
 * 톤은 중립으로 떨어뜨린다. 모르는 상태를 성공·실패 색으로 칠하지 않기 위해서다.
 */
export function statusLabelOf<K extends string>(
  table: Readonly<Record<K, StatusLabelWithIcon>>,
  key: string,
  scope = "labels",
): StatusLabelWithIcon {
  const hit = (table as Readonly<Record<string, StatusLabelWithIcon | undefined>>)[key];
  if (hit === undefined) {
    warnUnknownKey(key, scope);
    return { label: key, tone: "neutral" };
  }
  return hit;
}

/** 값이 null 또는 undefined 면 무데이터 표기로 바꾼다. */
export function orEmptyCell(value: string | number | null | undefined): string {
  return value === null || value === undefined ? EMPTY_CELL : String(value);
}
