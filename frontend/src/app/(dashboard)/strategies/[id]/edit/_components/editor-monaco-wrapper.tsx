// Monaco Pine 에디터를 파일 탭 toolbar 로 감싸는 wrapper (Sprint 43 W9-fidelity)
// prototype 01: file-tab primary(코퍼) top border + .editor-toolbar + JetBrains Mono.
// Terminal Tape 롤아웃: 하드코딩 다크 hex/slate → 테마 토큰으로 교체해 앱 라이트/다크에 함께 flip.
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
      className="flex flex-col overflow-hidden rounded-[var(--radius-md,0.625rem)] border border-border bg-card"
      data-testid="editor-monaco-wrapper"
    >
      {/* prototype 01: .editor-toolbar 36px / muted / file-tab primary(코퍼) 보더 */}
      <div className="flex h-9 shrink-0 items-center gap-2 border-b border-border bg-muted px-3">
        <div
          className="-mb-px inline-flex items-center gap-2 rounded-t-md border-t-2 border-[color:var(--primary)] bg-card px-3 py-1.5 font-mono text-[0.75rem] text-foreground"
          data-testid="editor-monaco-wrapper-filetab"
        >
          <FileIcon
            aria-hidden
            className="size-3 text-[color:var(--primary)]"
            strokeWidth={2}
          />
          <span>{fileName}</span>
          <span className="font-mono text-[0.7rem] text-muted-foreground">{versionLabel}</span>
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
      className="grid size-7 place-items-center rounded text-muted-foreground transition-colors hover:bg-[color:var(--border)] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {children}
    </button>
  );
}
