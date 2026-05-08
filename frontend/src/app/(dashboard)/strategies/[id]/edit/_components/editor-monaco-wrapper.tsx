// Monaco Pine 에디터를 prototype 1:1 다크 toolbar 로 감싸는 wrapper (Sprint 43 W9-fidelity)
// prototype 01: file-tab orange top border + .editor-toolbar 다크 + JetBrains Mono.
// PineEditor 자체는 이미 다크 theme 이지만, 외곽 toolbar 와 inset ring 으로 prototype 정합 완성.
"use client";

import { FileIcon, MaximizeIcon, SearchIcon } from "lucide-react";

import { PineEditor, type PineEditorProps } from "@/components/monaco/pine-editor";

export interface EditorMonacoWrapperProps extends PineEditorProps {
  /** 파일 탭에 표시할 파일명 (예: ma_crossover.pine) */
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
      className="flex flex-col overflow-hidden rounded-[var(--radius-md,0.625rem)] bg-[#1E1E1E] ring-1 ring-inset ring-white/5"
      data-testid="editor-monaco-wrapper"
    >
      {/* prototype 01: .editor-toolbar 36px / #252526 / file-tab orange 보더 */}
      <div className="flex h-9 shrink-0 items-center gap-2 border-b border-[#1a1a1a] bg-[#252526] px-3">
        <div
          className="-mb-px inline-flex items-center gap-2 rounded-t-md border-t-2 border-[#FB923C] bg-[#1E1E1E] px-3 py-1.5 font-mono text-[0.75rem] text-slate-200"
          data-testid="editor-monaco-wrapper-filetab"
        >
          <FileIcon
            aria-hidden
            className="size-3 text-[#FB923C]"
            strokeWidth={2}
          />
          <span>{fileName}</span>
          <span className="font-mono text-[0.7rem] text-slate-500">{versionLabel}</span>
        </div>

        <div className="ml-auto flex items-center gap-1">
          <ToolbarIconButton ariaLabel="찾기 (Cmd+F)">
            <SearchIcon className="size-3.5" aria-hidden strokeWidth={2} />
          </ToolbarIconButton>
          <ToolbarIconButton ariaLabel="전체화면">
            <MaximizeIcon className="size-3.5" aria-hidden strokeWidth={2} />
          </ToolbarIconButton>
        </div>
      </div>

      {/* Monaco editor 본체 — JetBrains Mono 는 PineEditor options 에서 이미 지정 */}
      <div className="min-h-0 flex-1">
        <PineEditor {...editorProps} />
      </div>
    </div>
  );
}

interface ToolbarIconButtonProps {
  ariaLabel: string;
  children: React.ReactNode;
}

function ToolbarIconButton({ ariaLabel, children }: ToolbarIconButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      className="grid size-7 place-items-center rounded text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/40"
    >
      {children}
    </button>
  );
}
