// Monaco Pine 에디터를 파일 탭 toolbar 로 감싸는 wrapper — C 디자인 언어 이식 (screen-08 소스).
// C 토큰(--line/--card/--card-2/--copper/--ink)만 쓰고 단일 반경(var(--r))을 지킨다. 자체
// 포커스 링(focus-visible:ring)은 제거해 전역 :focus-visible 카퍼 링만 걸리게 한다.
"use client";

import { FileIcon, MaximizeIcon, SearchIcon } from "lucide-react";

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

        <div className="ml-auto flex items-center gap-1">
          <ToolbarIconButton ariaLabel="찾기 (Cmd+F)">
            <SearchIcon className="size-3.5" aria-hidden strokeWidth={2} />
          </ToolbarIconButton>
          <ToolbarIconButton ariaLabel="전체화면">
            <MaximizeIcon className="size-3.5" aria-hidden strokeWidth={2} />
          </ToolbarIconButton>
        </div>
      </div>

      {/* Monaco editor 본체 */}
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

// 자체 포커스 링 없음 — 전역 언레이어드 :focus-visible 카퍼 링이 대신 걸린다.
function ToolbarIconButton({ ariaLabel, children }: ToolbarIconButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      className="grid size-7 place-items-center rounded-[var(--r)] text-[color:var(--ink-3)] transition-colors hover:bg-[color:var(--card-3)] hover:text-[color:var(--ink)]"
    >
      {children}
    </button>
  );
}
