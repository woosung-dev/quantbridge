// Monaco Pine v5 언어 등록 (Monarch tokenizer + pine-dark / pine-light 테마)
// Precision Instrument v3: 카본/스틸 팔레트 — Monaco 는 CSS 변수를 못 읽으므로
// BRAND_PALETTE(lib/brand-palette.ts) hex 상수를 직접 소비 (DESIGN.md §2.3).
// Sprint 7d+: autocomplete 등록 검토 (registerCompletionItemProvider)

import type { Monaco } from "@monaco-editor/react";
import { BRAND_PALETTE } from "@/lib/brand-palette";

const DARK = BRAND_PALETTE.dark;
const LIGHT = BRAND_PALETTE.light;

// 에디터 웰 전용 로컬 상수 — brand-palette 파생 (Monaco 소비처 한정).
// 다크: 카드(#141619)보다 깊은 웰 배경으로 코드 영역을 한 단계 가라앉힘.
//   #111316 = dark.bg(#0b0d0f) ↔ dark.card(#141619) 사이 보간.
//   #0e1013 = 웰보다 살짝 깊은 gutter. #565d66 = dark.textMuted 보다 낮은 대비의 라인 번호.
// 라이트: #9aa1a9 = light.textMuted 보다 낮은 대비의 라인 번호.
const EDITOR_DARK_BG = "#111316";
const EDITOR_DARK_GUTTER_BG = "#0e1013";
const EDITOR_DARK_LINE_NUMBER = "#565d66";
const EDITOR_LIGHT_LINE_NUMBER = "#9aa1a9";

/** Monarch token rule 은 `#` 없는 hex 문자열을 기대한다. */
function hex(color: string): string {
  return color.replace("#", "");
}

let _registered = false;

/** idempotent — Monaco 인스턴스에 Pine v5 언어를 1회만 등록. */
export function registerPineLanguage(monaco: Monaco): void {
  if (_registered) return;

  monaco.languages.register({ id: "pine" });

  monaco.languages.setMonarchTokensProvider("pine", {
    defaultToken: "",
    tokenPostfix: ".pine",

    keywords: [
      "strategy",
      "indicator",
      "library",
      "if",
      "else",
      "for",
      "to",
      "by",
      "while",
      "switch",
      "case",
      "default",
      "true",
      "false",
      "na",
      "var",
      "varip",
      "input",
      "and",
      "or",
      "not",
      "break",
      "continue",
      "return",
      "export",
      "import",
      "method",
      "type",
    ],

    // Pine v5 주요 built-in 함수 (접두어 포함). Monarch 매칭은 dotted 식별자 단위.
    functions: [
      "ta.sma",
      "ta.ema",
      "ta.wma",
      "ta.rsi",
      "ta.macd",
      "ta.atr",
      "ta.stoch",
      "ta.crossover",
      "ta.crossunder",
      "ta.highest",
      "ta.lowest",
      "ta.change",
      "strategy.entry",
      "strategy.exit",
      "strategy.close",
      "strategy.cancel",
      "input.int",
      "input.float",
      "input.bool",
      "input.string",
      "input.timeframe",
      "math.abs",
      "math.max",
      "math.min",
      "math.round",
      "plot",
      "plotshape",
      "plotchar",
      "hline",
      "request.security",
    ],

    operators: ["=", "==", "!=", "<", ">", "<=", ">=", "+", "-", "*", "/", "%", ":=", "?", ":"],

    symbols: /[=><!~?:&|+\-*/^%]+/,

    tokenizer: {
      root: [
        [/\/\/.*$/, "comment"],
        [/"([^"\\]|\\.)*$/, "string.invalid"],
        [/"/, { token: "string.quote", bracket: "@open", next: "@string" }],
        [/\d+\.\d+([eE][-+]?\d+)?/, "number.float"],
        [/\d+/, "number"],
        [
          /[a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)+/,
          {
            cases: {
              "@functions": "type.identifier",
              "@default": "identifier",
            },
          },
        ],
        [
          /[a-zA-Z_]\w*/,
          {
            cases: {
              "@keywords": "keyword",
              "@default": "identifier",
            },
          },
        ],
        [
          /@symbols/,
          {
            cases: {
              "@operators": "operator",
              "@default": "",
            },
          },
        ],
        [/[{}()[\]]/, "@brackets"],
        [/[,.;]/, "delimiter"],
        [/\s+/, "white"],
      ],
      string: [
        [/[^\\"]+/, "string"],
        [/\\./, "string.escape"],
        [/"/, { token: "string.quote", bracket: "@close", next: "@pop" }],
      ],
    },
  });

  // pine-dark — 카본/스틸 에디터 웰. keyword=코퍼 / string=bullish / type=benchmark /
  // number=compare — 차트 시리즈 어휘와 동일한 브랜드 색으로 통일 (DESIGN.md §2.3).
  monaco.editor.defineTheme("pine-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: hex(DARK.textMuted), fontStyle: "italic" },
      { token: "keyword", foreground: hex(DARK.primary) },
      { token: "type.identifier", foreground: hex(DARK.chartBenchmark) },
      { token: "identifier", foreground: hex(DARK.textPrimary) },
      { token: "string", foreground: hex(DARK.bullish) },
      { token: "string.quote", foreground: hex(DARK.bullish) },
      { token: "string.escape", foreground: hex(DARK.bullish) },
      { token: "number", foreground: hex(DARK.chartCompare) },
      { token: "number.float", foreground: hex(DARK.chartCompare) },
      { token: "operator", foreground: hex(DARK.textSecondary) },
    ],
    colors: {
      "editor.background": EDITOR_DARK_BG,
      "editor.foreground": DARK.textPrimary,
      "editor.lineHighlightBackground": DARK.cardRaised,
      "editorLineNumber.foreground": EDITOR_DARK_LINE_NUMBER,
      "editorGutter.background": EDITOR_DARK_GUTTER_BG,
    },
  });

  // pine-light — 쿨 페이퍼 위 화이트 웰. pine-dark 토큰 규칙을 라이트 팔레트로 미러링.
  monaco.editor.defineTheme("pine-light", {
    base: "vs",
    inherit: true,
    rules: [
      { token: "comment", foreground: hex(LIGHT.textMuted), fontStyle: "italic" },
      { token: "keyword", foreground: hex(LIGHT.primary) },
      { token: "type.identifier", foreground: hex(LIGHT.chartBenchmark) },
      { token: "identifier", foreground: hex(LIGHT.textPrimary) },
      { token: "string", foreground: hex(LIGHT.bullish) },
      { token: "string.quote", foreground: hex(LIGHT.bullish) },
      { token: "string.escape", foreground: hex(LIGHT.bullish) },
      { token: "number", foreground: hex(LIGHT.chartCompare) },
      { token: "number.float", foreground: hex(LIGHT.chartCompare) },
      { token: "operator", foreground: hex(LIGHT.textSecondary) },
    ],
    colors: {
      "editor.background": LIGHT.card,
      "editor.foreground": LIGHT.textPrimary,
      "editor.lineHighlightBackground": LIGHT.bgAlt,
      "editorLineNumber.foreground": EDITOR_LIGHT_LINE_NUMBER,
      "editorGutter.background": LIGHT.bg,
    },
  });

  _registered = true;
}
