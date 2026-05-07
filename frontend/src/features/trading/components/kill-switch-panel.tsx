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

  return (
    <section className="p-4 border rounded">
      <h2 className="font-semibold mb-3">Kill Switch</h2>
      {active.length === 0 ? (
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
                className="px-2 py-1 bg-red-500 text-white text-xs rounded disabled:opacity-50"
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
