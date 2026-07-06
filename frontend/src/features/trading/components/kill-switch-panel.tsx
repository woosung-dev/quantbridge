"use client";

// Kill Switch panel — active 시 destructive ring pulse / 해결 버튼 destructive variant.
// Sprint 44 W C4 — 해결 버튼 visual 통일 (ring focus + hover lift + transition 명시).

import { useKillSwitchEvents, useResolveKillSwitchEvent } from "../hooks";

export function KillSwitchPanel() {
  const { data, isError } = useKillSwitchEvents();
  const resolve = useResolveKillSwitchEvent();

  if (isError) {
    return (
      <section className="p-4 border rounded">
        <p className="text-sm text-destructive">
          Kill Switch 상태를 불러오지 못했습니다.
        </p>
      </section>
    );
  }
  if (!data) return null;

  const active = data.items.filter((e) => !e.resolved_at);
  const hasActiveDanger = active.length > 0;

  // Sprint 44 W F3 — active 시 red ring pulse + border destructive 강조. inactive 는 평온한 정적 스타일.
  return (
    <section
      data-testid="kill-switch-panel"
      data-state={hasActiveDanger ? "active" : "ok"}
      className={
        hasActiveDanger
          ? "qb-danger-pulse rounded border border-destructive bg-destructive-light/30 p-4 transition-colors"
          : "rounded border bg-card p-4 transition-colors"
      }
    >
      <h2 className="font-semibold mb-3 flex items-center gap-2">
        Kill Switch
        {hasActiveDanger ? (
          <span
            aria-label="Kill Switch 활성"
            className="inline-flex items-center gap-1.5 rounded-[4px] bg-destructive px-2 py-0.5 font-mono text-[10px] font-bold tracking-wider text-destructive-foreground uppercase"
          >
            <span className="size-1.5 rounded-full bg-current" />
            활성
          </span>
        ) : null}
      </h2>
      {!hasActiveDanger ? (
        <p className="text-success">이상 없음</p>
      ) : (
        <ul>
          {active.map((e) => (
            <li
              key={e.id}
              className="flex flex-wrap items-center justify-between gap-2 border-b py-2"
            >
              <span className="min-w-0 break-words">
                {e.trigger_type}: {e.trigger_value} / {e.threshold}
              </span>
              {/* Wave 2 — 모바일 터치타겟 ≥44pt (min-h-11 + min-w-11). */}
              <button
                type="button"
                onClick={() => resolve.mutate(e.id)}
                disabled={resolve.isPending}
                className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-md bg-destructive px-3 py-2 text-sm font-semibold text-destructive-foreground transition-colors duration-200 hover:opacity-90 focus-visible:ring-2 focus-visible:ring-destructive/40 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              >
                {resolve.isPending ? "처리 중…" : "해결"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
