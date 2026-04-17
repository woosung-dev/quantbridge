"use client";

// Sprint 7c T4: Monaco Pine editor 래퍼 — next/dynamic + ssr:false로 bundle 분리.
// ⌘+Enter / Ctrl+Enter 커맨드 등록 → 상위 onTriggerParse delegate.

import dynamic from "next/dynamic";
import type { OnMount } from "@monaco-editor/react";
import { registerPineLanguage } from "./pine-language";

// Monaco는 bundle size가 커서 client-only + dynamic import.
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  { ssr: false, loading: () => <div className="h-full animate-pulse rounded-md bg-[#0F172A]" /> },
);

export interface PineEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  onTriggerParse?: () => void;
}

export function PineEditor(props: PineEditorProps) {
  const handleMount: OnMount = (editor, monaco) => {
    registerPineLanguage(monaco);
    // ⌘+Enter / Ctrl+Enter → 상위로 파싱 트리거 delegate.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      props.onTriggerParse?.();
    });
  };

  return (
    <MonacoEditor
      height={props.height ?? 400}
      defaultLanguage="pine"
      theme="pine-dark"
      value={props.value}
      onChange={(v) => props.onChange(v ?? "")}
      onMount={handleMount}
      options={{
        readOnly: props.readOnly,
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
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
