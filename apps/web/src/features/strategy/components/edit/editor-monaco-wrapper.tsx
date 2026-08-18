// Monaco Pine 에디터를 파일 탭 toolbar 로 감싸는 wrapper — C 디자인 언어 이식 (screen-08 소스).
// C 토큰(--line/--card/--card-2/--copper/--ink)만 쓰고 단일 반경(var(--r))을 지킨다.
// toolbar 우측 아이콘 버튼(찾기/전체화면)은 screen-08 에 없는 발명 UI 라 두지 않는다 (가짜 UI 방지).
"use client";

import { FileIcon } from "lucide-react";

import { PineEditor, type PineEditorProps } from "@/components/monaco/pine-editor";

export interface EditorMonacoWrapperProps extends PineEditorProps {
  /** 파일 탭에 표시할 파일명 (예: strategy.pine) */
  fileName?: string;
  /** Pine 버전 라벨 (toolbar 우측 표시) */
  versionLabel?: string;
}

export function EditorMonacoWrapper({
  fileName = "strategy.pine",
  versionLabel = "Pine v5",
  ...editorProps
}: EditorMonacoWrapperProps) {
  return (
    <div
      className="flex flex-col overflow-hidden rounded-[var(--r)] border border-[color:var(--line)] bg-[color:var(--bg-alt)]"
      data-testid="editor-monaco-wrapper"
    >
      {/* 파일 탭 toolbar 36px — file-tab 은 코퍼 상단 보더로 활성 파일을 표시 */}
      <div className="flex h-9 shrink-0 items-center gap-2 border-b border-[color:var(--line)] bg-[color:var(--card-2)] px-3">
        <div
          className="-mb-px inline-flex items-center gap-2 rounded-t-[var(--r)] border-t-2 border-[color:var(--copper)] bg-[color:var(--card)] px-3 py-1.5 font-mono text-[0.75rem] text-[color:var(--ink)]"
          data-testid="editor-monaco-wrapper-filetab"
        >
          <FileIcon aria-hidden className="size-3 text-[color:var(--copper)]" strokeWidth={2} />
          <span>{fileName}</span>
          <span className="font-mono text-[0.7rem] text-[color:var(--ink-3)]">{versionLabel}</span>
        </div>
      </div>

      {/* Monaco editor 본체 */}
      <div className="min-h-0 flex-1">
        <PineEditor {...editorProps} />
      </div>
    </div>
  );
}
