"use client";

import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { ibmPlexMono } from "@/lib/fonts";

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((module) => module.default),
  {
    ssr: false,
    loading: () => <p className="p-4 text-muted-foreground">코드 편집기 불러오는 중…</p>,
  },
);

export function PythonEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const { resolvedTheme } = useTheme();
  return (
    <MonacoEditor
      height={360}
      language="python"
      theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
      value={value}
      onChange={(next) => onChange(next ?? "")}
      options={{
        ariaLabel: "Python 전략 코드",
        fontFamily: ibmPlexMono.style.fontFamily,
        fontSize: 13,
        lineHeight: 20,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        tabSize: 4,
        padding: { top: 16, bottom: 16 },
      }}
    />
  );
}
