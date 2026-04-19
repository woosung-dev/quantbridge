"use client";

import { useEffect, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// 전역 `?` 단축키 도움말 Dialog.
// 입력 영역(input/textarea/contentEditable) focus 중에는 `?` 타이핑을 방해하지 않도록 무시.
// Esc 로 닫기는 Base UI Dialog 내장 동작.

type Shortcut = {
  keys: readonly string[];
  label: string;
  scope: string;
};

const SHORTCUTS: readonly Shortcut[] = [
  { keys: ["⌘", "S"], label: "저장", scope: "전략 편집" },
  { keys: ["⌘", "Enter"], label: "파싱 실행", scope: "전략 편집" },
  { keys: ["?"], label: "이 도움말 열기", scope: "전역" },
  { keys: ["Esc"], label: "닫기", scope: "전역" },
];

function isEditableTarget(el: Element | null): boolean {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el instanceof HTMLElement) {
    if (el.isContentEditable) return true;
    // jsdom fallback: `isContentEditable` 구현이 일부 환경에서 누락되어 속성 기반으로도 확인.
    const attr = el.getAttribute("contenteditable");
    if (attr === "" || attr === "true" || attr === "plaintext-only") return true;
  }
  return false;
}

export function ShortcutHelpDialog() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented) return;
      if (event.isComposing || event.repeat) return;
      if (event.key !== "?") return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (isEditableTarget(document.activeElement)) return;

      event.preventDefault();
      setOpen(true);
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent aria-describedby="shortcut-help-description">
        <DialogHeader>
          <DialogTitle>키보드 단축키</DialogTitle>
          <DialogDescription id="shortcut-help-description">
            자주 쓰는 동작을 키보드로 바로 실행할 수 있어요.
          </DialogDescription>
        </DialogHeader>

        <ul className="mt-2 flex flex-col gap-2" data-testid="shortcut-list">
          {SHORTCUTS.map((shortcut) => (
            <li
              key={shortcut.label}
              className="flex items-center justify-between gap-3 rounded-md border border-[color:var(--border)] bg-[color:var(--muted)]/40 px-3 py-2"
            >
              <div className="flex items-center gap-1.5">
                {shortcut.keys.map((k, idx) => (
                  <span key={`${shortcut.label}-${idx}`} className="flex items-center gap-1.5">
                    {idx > 0 && (
                      <span
                        aria-hidden="true"
                        className="text-xs text-[color:var(--muted-foreground)]"
                      >
                        +
                      </span>
                    )}
                    <kbd className="inline-flex min-w-[1.75rem] items-center justify-center rounded border border-[color:var(--border)] bg-[color:var(--card)] px-1.5 py-0.5 font-mono text-xs font-medium text-[color:var(--foreground)] shadow-sm">
                      {k}
                    </kbd>
                  </span>
                ))}
              </div>
              <div className="flex flex-col items-end text-right">
                <span className="text-sm font-medium text-[color:var(--foreground)]">
                  {shortcut.label}
                </span>
                <span className="text-xs text-[color:var(--muted-foreground)]">
                  {shortcut.scope}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
