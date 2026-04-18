// Sprint FE-01: Pine 식별자 자연어 해설 테이블 + 에러/경고 조치 lookup.
// 하드코딩, LLM 호출 없음, 오프라인 결정적.

import type { ParseError } from "@/features/strategy/schemas";

export type PineFunctionDescription = {
  summary: string;
  purpose: string;
  example?: string;
};

export type ErrorAdvice = { what: string; action: string };
export type WarningAdvice = { what: string; action: string };

export const PINE_FUNCTION_LEXICON: Record<string, PineFunctionDescription> = {
  "ta.sma": {
    summary: "단순 이동평균(SMA)",
    purpose: "최근 N봉 종가의 산술 평균을 추세선으로 사용",
    example: "ta.sma(close, 20)",
  },
  "ta.ema": {
    summary: "지수 이동평균(EMA)",
    purpose: "최근 가격에 더 큰 가중치를 두는 추세선",
    example: "ta.ema(close, 12)",
  },
  "ta.rma": {
    summary: "Wilder 이동평균(RMA)",
    purpose: "RSI/ATR 계산에 쓰이는 smoothed 평균",
    example: "ta.rma(source, 14)",
  },
  "ta.rsi": {
    summary: "상대강도지수(RSI)",
    purpose: "가격 모멘텀을 0-100 범위로 측정해 과매수/과매도 판별",
    example: "ta.rsi(close, 14)",
  },
  "ta.atr": {
    summary: "평균 진폭(ATR)",
    purpose: "최근 변동성을 측정해 손절 폭·포지션 사이징에 활용",
    example: "ta.atr(14)",
  },
  "ta.stdev": {
    summary: "표준편차",
    purpose: "가격 분산의 통계적 측정 (볼린저밴드 등에 사용)",
    example: "ta.stdev(close, 20)",
  },
  "ta.crossover": {
    summary: "상향 크로스",
    purpose: "이전 봉에서 아래, 현재 봉에서 위에 있는 순간을 true로",
    example: "ta.crossover(fast, slow)",
  },
  "ta.crossunder": {
    summary: "하향 크로스",
    purpose: "이전 봉에서 위, 현재 봉에서 아래에 있는 순간을 true로",
    example: "ta.crossunder(fast, slow)",
  },
  "ta.cross": {
    summary: "양방향 크로스",
    purpose: "방향 무관 교차 순간 true",
    example: "ta.cross(a, b)",
  },
  "ta.highest": {
    summary: "최근 N봉 최고값",
    purpose: "롤링 최고가 계산 (돌파 전략에 사용)",
    example: "ta.highest(high, 20)",
  },
  "ta.lowest": {
    summary: "최근 N봉 최저값",
    purpose: "롤링 최저가 계산 (이탈·지지선 전략에 사용)",
    example: "ta.lowest(low, 20)",
  },
  "ta.change": {
    summary: "차이값",
    purpose: "현재값 - N봉 전 값",
    example: "ta.change(close, 1)",
  },
  nz: {
    summary: "NaN 대체",
    purpose: "NaN을 0(또는 지정값)으로 변환",
    example: "nz(value, 0)",
  },
  na: {
    summary: "NaN 체크",
    purpose: "값이 NaN인지 검사",
    example: "na(value)",
  },
  strategy: {
    summary: "전략 선언",
    purpose: "스크립트를 전략 모드로 정의하고 기본 옵션 설정",
    example: 'strategy("name", overlay=true)',
  },
  "strategy.entry": {
    summary: "진입 주문",
    purpose: "롱/숏 포지션 진입을 예약 (조건 충족 시 다음 봉에서 체결)",
    example: 'strategy.entry("long", strategy.long)',
  },
  "strategy.exit": {
    summary: "청산 주문",
    purpose: "stop/limit/trail 중 하나로 포지션 청산 조건 예약",
    example: 'strategy.exit("tp", "long", profit=100)',
  },
  "strategy.close": {
    summary: "즉시 청산",
    purpose: "지정된 엔트리 ID를 시장가로 즉시 닫음",
    example: 'strategy.close("long")',
  },
  "strategy.long": {
    summary: "롱 방향 상수",
    purpose: "strategy.entry의 direction 인자로 사용",
    example: "strategy.long",
  },
  "strategy.short": {
    summary: "숏 방향 상수",
    purpose: "strategy.entry의 direction 인자로 사용",
    example: "strategy.short",
  },
  input: {
    summary: "사용자 입력",
    purpose: "차트에서 조정 가능한 파라미터 정의 (v4 레거시 함수)",
    example: "input(14, 'length')",
  },
  "input.int": {
    summary: "정수 입력",
    purpose: "정수형 파라미터를 차트에서 조정 가능하게 노출",
    example: 'input.int(14, "length", minval=1)',
  },
  "input.bool": {
    summary: "불리언 입력",
    purpose: "참/거짓 토글 파라미터 (신호 on/off 등)",
    example: 'input.bool(true, "enable filter")',
  },
  "input.string": {
    summary: "문자열 입력",
    purpose: "문자열 파라미터 (옵션 선택 포함)",
    example: 'input.string("EMA", options=["SMA","EMA"])',
  },
  "input.float": {
    summary: "실수 입력",
    purpose: "실수형 파라미터 (배수, 임계치 등)",
    example: 'input.float(1.5, "multiplier", step=0.1)',
  },
  "input.color": {
    summary: "색상 입력",
    purpose: "차트 요소 색상을 사용자 조정 가능하게 노출",
    example: 'input.color(color.green, "up color")',
  },
  "input.source": {
    summary: "가격 소스 입력",
    purpose: "계산 대상 가격을 open/high/low/close/hl2 등에서 선택",
    example: 'input.source(close, "source")',
  },
  "input.symbol": {
    summary: "심볼 입력",
    purpose: "다른 종목 심볼을 파라미터로 선택 (MTF / 페어 비교)",
    example: 'input.symbol("BTCUSDT", "reference")',
  },
  "input.timeframe": {
    summary: "타임프레임 입력",
    purpose: "분봉/시봉/일봉 등 타임프레임 선택 (MTF 전략)",
    example: 'input.timeframe("15", "timeframe")',
  },
  "input.session": {
    summary: "세션 입력",
    purpose: "거래 세션 시간대 선택 (예: 09:00-15:30)",
    example: 'input.session("0930-1530", "session")',
  },
  "input.time": {
    summary: "시간 입력",
    purpose: "특정 시각을 timestamp로 선택",
    example: 'input.time(timestamp("2026-01-01"), "start")',
  },
  "input.price": {
    summary: "가격 입력",
    purpose: "차트에서 직접 가격 레벨을 찍어 파라미터로 사용",
    example: 'input.price(100.0, "target")',
  },
  plot: {
    summary: "선 그리기",
    purpose: "차트에 값을 시각화",
    example: "plot(ema20, color=color.blue)",
  },
  alert: {
    summary: "알림",
    purpose: "조건 충족 시 TradingView 알림 발생",
    example: 'alert("cross", alert.freq_once_per_bar)',
  },
};

const ERROR_ADVICE_TABLE: Record<string, ErrorAdvice> = {
  function: {
    what: "지원하지 않는 함수가 호출되었습니다.",
    action: "Pine v5 지원 함수 목록으로 교체하거나, 간이 구현으로 대체해보세요.",
  },
  syntax: {
    what: "구문 오류가 발견되었습니다.",
    action: "해당 라인의 괄호 균형과 연산자 위치를 확인하세요.",
  },
  type: {
    what: "타입이 일치하지 않습니다 (예: int ↔ float, series ↔ simple).",
    action: "인자의 타입을 맞추거나 `float()` 같은 명시적 캐스트를 추가하세요.",
  },
  v4_migration: {
    what: "v4 문법을 v5가 지원하지 않습니다.",
    action: "함수 앞에 `ta.` 또는 `math.` prefix를 붙여보세요. (예: `rsi` → `ta.rsi`)",
  },
  PineLexError: {
    what: "토크나이저가 문자 시퀀스를 해석하지 못했습니다.",
    action: "해당 라인의 특수 문자나 인용부호를 확인하세요.",
  },
  PineParseError: {
    what: "파서가 문법 구조를 인식하지 못했습니다.",
    action: "이전 라인의 `=>`, `:=` 같은 키워드 누락 여부를 점검하세요.",
  },
  PineRuntimeError: {
    what: "실행 중 오류가 발생했습니다.",
    action: "변수 정의 순서와 `na` 처리를 확인하세요.",
  },
  PineUnsupportedError: {
    what: "이 버전에서 지원하지 않는 기능입니다.",
    action: "해당 함수/객체를 지원되는 대체 구현으로 교체하세요.",
  },
};

export function describeFunction(name: string): PineFunctionDescription {
  const hit = PINE_FUNCTION_LEXICON[name];
  if (hit) return hit;
  return {
    summary: name,
    purpose: "해설이 등록되지 않은 식별자입니다. Pine 공식 문서를 확인하세요.",
  };
}

export function adviseError(error: ParseError): ErrorAdvice {
  const known = ERROR_ADVICE_TABLE[error.code];
  if (known) return known;
  return {
    what: "알 수 없는 오류가 발생했습니다.",
    action:
      error.line != null
        ? `라인 ${error.line} 주변을 수동으로 점검해주세요.`
        : "에러 메시지 내용을 기반으로 수동 점검이 필요합니다.",
  };
}

export function adviseWarning(message: string): WarningAdvice {
  if (message.includes("duplicate strategy.exit")) {
    return {
      what: "같은 전략에 strategy.exit 콜이 여러 번 선언되어 있습니다.",
      action:
        "마지막 호출만 반영됩니다. stop/limit을 중첩 설정하려 했다면 하나의 strategy.exit 호출로 합치세요.",
    };
  }
  return {
    what: "주의가 필요한 패턴이 감지되었습니다.",
    action: "메시지 내용을 확인하고 의도된 동작인지 점검하세요.",
  };
}
