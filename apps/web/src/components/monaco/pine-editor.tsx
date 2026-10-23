"use client";

// Sprint 7c T4: Monaco Pine editor 래퍼 — next/dynamic + ssr:false로 bundle 분리.
// ⌘+Enter / Ctrl+Enter 커맨드 등록 → 상위 onTriggerParse delegate.

import dynamic from "next/dynamic";
import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, type Ref } from "react";
import { useTheme } from "next-themes";
import type { BeforeMount, EditorProps, OnMount } from "@monaco-editor/react";
import { ibmPlexMono } from "@/lib/fonts";
import { registerPineLanguage } from "./pine-language";

// Monaco는 bundle size가 커서 client-only + dynamic import.
const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
  loading: () => <div className="h-full animate-pulse rounded-md bg-muted" />,
});

export interface PineEditorHandle {
  revealLine1: (line: number) => boolean;
}

export interface PineEditorProps {
  ref?: Ref<PineEditorHandle>;
  value: string;
  onChange: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  onTriggerParse?: () => void;
}

type MonacoEditorInstance = Parameters<OnMount>[0];
type MonacoNamespace = Parameters<OnMount>[1];

export function PineEditor(props: PineEditorProps) {
  const parseRef = useRef(props.onTriggerParse);
  const onChangeRef = useRef(props.onChange);
  const mountedEditorRef = useRef<{
    editor: MonacoEditorInstance;
    monaco: MonacoNamespace;
  } | null>(null);
  // H-3: render 중 ref 를 쓰지 않고 commit 마다 최신 callback 을 동기화한다.
  useEffect(() => {
    parseRef.current = props.onTriggerParse;
    onChangeRef.current = props.onChange;
  });

  // Monaco의 모델 listener는 유지하면서 최신 부모 callback에 변경 값을 전달한다.
  const handleChange = useCallback((value: string | undefined) => {
    onChangeRef.current(value ?? "");
  }, []);

  useImperativeHandle(
    props.ref,
    () => ({
      revealLine1(line) {
        if (!Number.isSafeInteger(line) || line < 1) return false;

        const mounted = mountedEditorRef.current;
        const model = mounted?.editor.getModel();
        if (!mounted || !model) return false;

        const targetLine = Math.min(line, model.getLineCount());
        if (targetLine < 1) return false;

        mounted.editor.revealLineInCenter(targetLine);
        mounted.editor.setSelection(new mounted.monaco.Selection(targetLine, 1, targetLine, 1));
        mounted.editor.focus();
        return true;
      },
    }),
    [],
  );

  // 앱 테마(next-themes)에 맞춰 Monaco 테마 선택. resolvedTheme 는 SSR/초기 렌더에서
  // undefined 일 수 있으므로 "dark" 일 때만 pine-dark, 그 외(undefined 포함)는 pine-light 로 fallback.
  // useTheme 객체 자체를 effect dep 으로 쓰지 않고 string 으로 파생 (LESSON H-1).
  const { resolvedTheme } = useTheme();
  const monacoTheme = resolvedTheme === "dark" ? "pine-dark" : "pine-light";

  // beforeMount: editor instance 생성 전에 language + 양쪽(pine-dark/pine-light) 테마 등록 (theme prop과 race 방지).
  const handleBeforeMount: BeforeMount = (monaco) => {
    registerPineLanguage(monaco);
  };

  const handleMount: OnMount = (editor, monaco) => {
    mountedEditorRef.current = { editor, monaco };
    // ⌘+Enter / Ctrl+Enter → 상위로 파싱 트리거 delegate.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      parseRef.current?.();
    });
  };

  // Monaco는 options 참조가 바뀔 때마다 updateOptions를 실행한다.
  const readOnly = props.readOnly;
  const options = useMemo<EditorProps["options"]>(
    () => ({
      readOnly: readOnly,
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
    }),
    [readOnly],
  );

  return (
    <MonacoEditor
      height={props.height ?? 400}
      defaultLanguage="pine"
      theme={monacoTheme}
      value={props.value}
      onChange={handleChange}
      beforeMount={handleBeforeMount}
      onMount={handleMount}
      options={options}
    />
  );
}
