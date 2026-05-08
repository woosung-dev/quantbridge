"use client";

import { useKillSwitchEvents, useResolveKillSwitchEvent } from "../hooks";

export function KillSwitchPanel() {
  const { data, isError } = useKillSwitchEvents();
  const resolve = useResolveKillSwitchEvent();

  if (isError) {
    return (
      <section className="p-4 border rounded">
        <p className="text-sm text-[color:var(--destructive)]">
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
          ? "qb-danger-pulse rounded border border-[color:var(--destructive)] bg-[color:var(--destructive-light)]/30 p-4 transition-colors"
          : "rounded border bg-card p-4 transition-colors"
      }
    >
      <h2 className="font-semibold mb-3 flex items-center gap-2">
        Kill Switch
        {hasActiveDanger ? (
          <span
            aria-label="Kill Switch 활성"
            className="inline-flex items-center gap-1.5 rounded-full bg-[color:var(--destructive)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white"
          >
            <span className="size-1.5 rounded-full bg-white" />
            활성
          </span>
        ) : null}
      </h2>
      {!hasActiveDanger ? (
        <p className="text-green-600">이상 없음</p>
      ) : (
        <ul>
          {active.map((e) => (
            <li
              key={e.id}
              className="flex justify-between items-center border-b py-1"
            >
              <span>
                {e.trigger_type}: {e.trigger_value} / {e.threshold}
              </span>
              <button
                type="button"
                onClick={() => resolve.mutate(e.id)}
                disabled={resolve.isPending}
                className="px-2 py-1 bg-red-500 text-white text-xs rounded transition-opacity hover:opacity-90 disabled:opacity-50"
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
