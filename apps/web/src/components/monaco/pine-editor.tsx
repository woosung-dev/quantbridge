"use client";

// Sprint 7c T4: Monaco Pine editor 래퍼 — next/dynamic + ssr:false로 bundle 분리.
// ⌘+Enter / Ctrl+Enter 커맨드 등록 → 상위 onTriggerParse delegate.

import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";
import type { BeforeMount, OnMount } from "@monaco-editor/react";
import { ibmPlexMono } from "@/lib/fonts";
import { registerPineLanguage } from "./pine-language";

// Monaco는 bundle size가 커서 client-only + dynamic import.
const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
  loading: () => <div className="h-full animate-pulse rounded-md bg-muted" />,
});

export interface PineEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  onTriggerParse?: () => void;
}

export function PineEditor(props: PineEditorProps) {
  // 앱 테마(next-themes)에 맞춰 Monaco 테마 선택. resolvedTheme 는 SSR/초기 렌더에서
  // undefined 일 수 있으므로 "dark" 일 때만 pine-dark, 그 외(undefined 포함)는 pine-light 로 fallback.
  // useTheme 객체 자체를 effect dep 으로 쓰지 않고 string 으로 파생 (LESSON H-1).
  const { resolvedTheme } = useTheme();
  const monacoTheme = resolvedTheme === "dark" ? "pine-dark" : "pine-light";

  // beforeMount: editor instance 생성 전에 language + 양쪽(pine-dark/pine-light) 테마 등록 (theme prop과 race 방지).
  const handleBeforeMount: BeforeMount = (monaco) => {
    registerPineLanguage(monaco);
  };

  // ★`addCommand` 는 마운트 때 **한 번** 등록된다. 콜백이 `props` 를 직접 잡으면 마운트 시점의
  //   `onTriggerParse` 가 영원히 불려, 부모가 매 렌더 넘기는 새 클로저(최신 소스)를 못 본다 —
  //   새 전략 위저드에서 ⌘+Enter 가 빈 초기 소스로 판정돼 아무 일도 안 했다.
  //   최신 콜백은 ref 로 읽는다(H-3: render body 대입 금지 → deps 없는 effect 에서 갱신).
  const onTriggerParseRef = useRef(props.onTriggerParse);
  useEffect(() => {
    onTriggerParseRef.current = props.onTriggerParse;
  });

  const handleMount: OnMount = (editor, monaco) => {
    // ⌘+Enter / Ctrl+Enter → 상위로 파싱 트리거 delegate.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      onTriggerParseRef.current?.();
    });
  };

  return (
    <MonacoEditor
      height={props.height ?? 400}
      defaultLanguage="pine"
      theme={monacoTheme}
      value={props.value}
      onChange={(v) => props.onChange(v ?? "")}
      beforeMount={handleBeforeMount}
      onMount={handleMount}
      options={{
        readOnly: props.readOnly,
        // Precision Instrument: IBM Plex Mono — next/font 가 생성한 해시 family 명을
        // 직접 주입 (Monaco 는 CSS 변수 해석 불가, 리터럴 "IBM Plex Mono" 금지 — lib/fonts.ts).
        fontFamily: ibmPlexMono.style.fontFamily,
        fontSize: 13,
        lineHeight: 20,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        tabSize: 4,
        renderLineHighlight: "line",
        smoothScrolling: true,
        padding: { top: 16, bottom: 16 },
      }}
    />
  );
}
