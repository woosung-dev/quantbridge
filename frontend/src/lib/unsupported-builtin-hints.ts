// Sprint 21 BL-095 — backend 의 422 unsupported_builtins list 를 사용자 친화 메시지로
// 변환. backend StrategyNotRunnable.detail.unsupported_builtins 의 각 항목 (예: "heikinashi",
// "request.security", "max") 에 대한 한국어 설명. mapping 미존재 시 builtin 이름 자체 반환.
//
// Trust Layer 정합 (codex G.0 P1 #2): heikinashi/security 는 silent corruption risk
// 로 Sprint 21 에서 unsupported 유지. 사용자에게는 정확한 사유를 명시.
//
// Sprint 32 E (BL-163) — backfill: Pine v6 collection types (array/matrix/map) +
// 누락 builtins (request.* 추가, syminfo.*, ta.* alternates). backend 의
// `coverage._UNSUPPORTED_WORKAROUNDS` SSOT 와 일관 (BE 단독 SSOT — FE 는 추가 정보 제공만).

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

  // Sprint 32 E (BL-163) — Pine v6 collection types backfill.
  // backend coverage._UNSUPPORTED_WORKAROUNDS 와 동기. paradigm mismatch — 단일
  // series 변수 또는 ta.* stateful 지표로 재구성 권장.
  "array.new_float": {
    hint: "Pine array<float> 미지원. 단일 series 변수 또는 ta.highest/lowest 등 stateful 지표로 대체.",
    category: "alternative",
  },
  "array.new_int": {
    hint: "Pine array<int> 미지원. 단일 series 변수 사용.",
    category: "alternative",
  },
  "array.new_bool": {
    hint: "Pine array<bool> 미지원. 단일 boolean series 변수 사용.",
    category: "alternative",
  },
  "array.new_string": {
    hint: "Pine array<string> 미지원. 단일 string 변수 사용.",
    category: "alternative",
  },
  "array.new_color": {
    hint: "Pine array<color> 미지원. 시각 NOP — 제거 권장.",
    category: "noop",
  },
  "array.new_line": {
    hint: "Pine array<line> 미지원. 시각 NOP — 단일 line 변수 사용.",
    category: "noop",
  },
  "array.new_label": {
    hint: "Pine array<label> 미지원. 시각 NOP — 단일 label 변수 사용.",
    category: "noop",
  },
  "array.new_box": {
    hint: "Pine array<box> 미지원. 시각 NOP — 단일 box 변수 사용.",
    category: "noop",
  },
  "array.new_table": {
    hint: "Pine array<table> 미지원. 시각 NOP — 단일 table 변수 사용.",
    category: "noop",
  },
  "array.push": {
    hint: "array.* 자체 미지원. 단일 series 변수로 재구성.",
    category: "alternative",
  },
  "array.pop": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "array.get": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "array.set": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "array.size": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "array.shift": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "array.unshift": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "array.clear": {
    hint: "array.* 자체 미지원 — 호출 불필요.",
    category: "alternative",
  },
  "matrix.new": {
    hint: "Pine matrix<T> 미지원. 2D 데이터는 외부 source 또는 다중 series 로 재구성.",
    category: "alternative",
  },
  "map.new": {
    hint: "Pine map<K,V> 미지원. dict-like 데이터는 lookup 변수로 재구성.",
    category: "alternative",
  },

  // Sprint 32 E (BL-163) — request.* / syminfo.* / ta.* 추가 backfill.
  "request.quandl": {
    hint: "Quandl 데이터 미지원. 외부 source 연동 필요.",
    category: "noop",
  },
  "request.financial": {
    hint: "재무 데이터 미지원. 외부 source 연동 필요.",
    category: "noop",
  },
  "ticker.new": {
    hint: "단일 ticker 사용 권장 (현재 backtest symbol).",
    category: "alternative",
  },
  "syminfo.prefix": {
    hint: "exchange prefix 는 backtest 에서 의미 없음. 변수 추출 권장.",
    category: "alternative",
  },
  "syminfo.ticker": {
    hint: "현재 backtest symbol 변수로 직접 사용.",
    category: "alternative",
  },
  "syminfo.timezone": {
    hint: "단일 timezone 가정 (UTC). timezone 분기 로직 제거 권장.",
    category: "alternative",
  },
  "ta.alma": {
    hint: "Arnaud Legoux MA 미지원. ta.sma 또는 ta.ema 로 근사 (정확도 차이 < 1%).",
    category: "alternative",
  },
  "ta.bb": {
    hint: "Bollinger Bands = ta.sma + ta.stdev 조합으로 직접 구현.",
    category: "alternative",
  },
  "ta.cross": {
    hint: "ta.crossover + ta.crossunder 조합으로 대체.",
    category: "alternative",
  },
  "ta.dmi": {
    hint: "Directional Movement Index = ta.atr + 직접 +DI/-DI 계산.",
    category: "alternative",
  },
  "ta.mom": {
    hint: "Momentum = close - close[length] 단순 계산.",
    category: "alternative",
  },
  "ta.wma": {
    hint: "Weighted MA = ta.sma 또는 ta.ema 로 근사.",
    category: "alternative",
  },
  "ta.obv": {
    hint: "On-Balance Volume = volume 누적 sum 으로 직접 구현.",
    category: "alternative",
  },
  fixnan: {
    hint: "nz() + 직전 값 캐싱 조합으로 대체 가능.",
    category: "alternative",
  },
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
