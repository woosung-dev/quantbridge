// Sprint 7c T4: Monaco Pine v5 언어 등록 (Monarch tokenizer + pine-dark 테마)
// DESIGN.md 07-strategy-create.html `--syntax-*` 변수 5색 팔레트 매핑.
// Sprint 7d+: autocomplete 등록 검토 (registerCompletionItemProvider)

import type { Monaco } from "@monaco-editor/react";

let _registered = false;

/** idempotent — Monaco 인스턴스에 Pine v5 언어를 1회만 등록. */
export function registerPineLanguage(monaco: Monaco): void {
  if (_registered) return;

  monaco.languages.register({ id: "pine" });

  monaco.languages.setMonarchTokensProvider("pine", {
    defaultToken: "",
    tokenPostfix: ".pine",

    keywords: [
      "strategy", "indicator", "library",
      "if", "else", "for", "to", "by", "while", "switch", "case", "default",
      "true", "false", "na",
      "var", "varip", "input",
      "and", "or", "not",
      "break", "continue", "return",
      "export", "import", "method", "type",
    ],

    // Pine v5 주요 built-in 함수 (접두어 포함). Monarch 매칭은 dotted 식별자 단위.
    functions: [
      "ta.sma", "ta.ema", "ta.wma", "ta.rsi", "ta.macd", "ta.atr", "ta.stoch",
      "ta.crossover", "ta.crossunder", "ta.highest", "ta.lowest", "ta.change",
      "strategy.entry", "strategy.exit", "strategy.close", "strategy.cancel",
      "input.int", "input.float", "input.bool", "input.string", "input.timeframe",
      "math.abs", "math.max", "math.min", "math.round",
      "plot", "plotshape", "plotchar", "hline",
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
        [/[a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)+/, {
          cases: {
            "@functions": "type.identifier",
            "@default": "identifier",
          },
        }],
        [/[a-zA-Z_]\w*/, {
          cases: {
            "@keywords": "keyword",
            "@default": "identifier",
          },
        }],
        [/@symbols/, {
          cases: {
            "@operators": "operator",
            "@default": "",
          },
        }],
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

  // DESIGN.md editor 토큰 색상 (07-strategy-create.html `--syntax-*` 변수 참조)
  monaco.editor.defineTheme("pine-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: "64748B", fontStyle: "italic" },
      { token: "keyword", foreground: "FB923C" },
      { token: "type.identifier", foreground: "60A5FA" },
      { token: "identifier", foreground: "F8FAFC" },
      { token: "string", foreground: "4ADE80" },
      { token: "string.quote", foreground: "4ADE80" },
      { token: "string.escape", foreground: "4ADE80" },
      { token: "number", foreground: "C084FC" },
      { token: "number.float", foreground: "C084FC" },
      { token: "operator", foreground: "CBD5E1" },
    ],
    colors: {
      "editor.background": "#1E293B",
      "editor.foreground": "#E2E8F0",
      "editor.lineHighlightBackground": "#0F172A",
      "editorLineNumber.foreground": "#475569",
      "editorGutter.background": "#0F172A",
    },
  });

  _registered = true;
}
