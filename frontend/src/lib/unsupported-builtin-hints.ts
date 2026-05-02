// Sprint 21 BL-095 — backend 의 422 unsupported_builtins list 를 사용자 친화 메시지로
// 변환. backend StrategyNotRunnable.detail.unsupported_builtins 의 각 항목 (예: "heikinashi",
// "request.security", "max") 에 대한 한국어 설명. mapping 미존재 시 builtin 이름 자체 반환.
//
// Trust Layer 정합 (codex G.0 P1 #2): heikinashi/security 는 silent corruption risk
// 로 Sprint 21 에서 unsupported 유지. 사용자에게는 정확한 사유를 명시.

export interface UnsupportedBuiltinHint {
  /** Pine 의 builtin 이름 (예: "heikinashi", "request.security"). */
  readonly name: string;
  /** 한국어 설명. 사용자 가 왜 reject 됐는지 + 가능하면 대체 권장. */
  readonly hint: string;
  /** 'corruption' = 결과 부정확 risk. 'noop' = 단순 미구현. 'alternative' = 대체 함수 권장. */
  readonly category: "corruption" | "noop" | "alternative";
}

const _HINTS: Record<string, Omit<UnsupportedBuiltinHint, "name">> = {
  // Trust Layer corruption risk (silent data corruption — Sprint 22+ strict toggle 검토)
  heikinashi: {
    hint: "헤이켄아시 변환 — 다른 종류 차트 데이터 의존 (현재 backtest 결과 부정확 risk).",
    category: "corruption",
  },
  security: {
    hint: "다른 timeframe 데이터 의존 (request.security v4 form). backtest 결과 부정확 risk.",
    category: "corruption",
  },
  "request.security": {
    hint: "다른 timeframe 데이터 의존. backtest 결과 부정확 risk.",
    category: "corruption",
  },
  "request.security_lower_tf": {
    hint: "하위 timeframe 데이터 의존. backtest 결과 부정확 risk.",
    category: "corruption",
  },
  "request.dividends": {
    hint: "배당 정보 의존 — 미지원.",
    category: "noop",
  },
  "request.earnings": {
    hint: "실적 발표 정보 의존 — 미지원.",
    category: "noop",
  },

  // Sprint 21 codex G.2 P2 — max/min/abs alias 는 fix 됐으므로 권장 hint 제거.
  // alias ordering fix 후 user function 우선 dispatch 되어 충돌 risk 사라짐.
  // legacy backend 응답 호환을 위해 fallback 메시지만 generic 처리.

  // Sprint 21 G.2 P1 #1 — timeframe.* 는 runtime 미구현으로 unsupported 유지.
  "timeframe.period": {
    hint: "현재 timeframe 식별자 — backtest runtime 미구현 (Sprint 22+ scope).",
    category: "noop",
  },
  "timeframe.multiplier": {
    hint: "현재 timeframe multiplier — runtime 미구현.",
    category: "noop",
  },
  "timeframe.isintraday": {
    hint: "intraday 여부 boolean — runtime 미구현.",
    category: "noop",
  },

  // 단순 noop / drawing primitive (Sprint 22+ 우선순위)
  barcolor: {
    hint: "차트 시각 효과만 — backtest 무관. Sprint 22+ NOP 처리 검토.",
    category: "noop",
  },
  "box.set_top": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
  "box.set_bottom": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
  "box.set_left": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
  "box.set_right": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
  "label.set_xy": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
  "label.set_text": {
    hint: "drawing primitive — Sprint 22+ scope.",
    category: "noop",
  },
  "label.set_color": {
    hint: "drawing primitive — Sprint 22+ scope.",
    category: "noop",
  },
  "line.set_xy1": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
  "line.set_xy2": { hint: "drawing primitive — Sprint 22+ scope.", category: "noop" },
};

/**
 * builtin 이름 (예: "heikinashi" 또는 "currency.USDXYZ123") 에 대한 친절 hint 반환.
 * mapping 미존재 시 generic fallback ({hint: "<name> — 미지원 빌트인", category: "noop"}).
 */
export function getUnsupportedBuiltinHint(name: string): UnsupportedBuiltinHint {
  const meta = _HINTS[name];
  if (meta) {
    return { name, ...meta };
  }
  return {
    name,
    hint: `${name} — 미지원 빌트인 (자세한 정책은 docs/02_domain/supported-indicators.md 참고).`,
    category: "noop",
  };
}

/** 다중 builtin 의 hint list. UI 카드 렌더링 용. */
export function getUnsupportedBuiltinHints(
  names: readonly string[],
): UnsupportedBuiltinHint[] {
  return names.map(getUnsupportedBuiltinHint);
}
