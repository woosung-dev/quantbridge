'use client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchKillSwitchEvents } from './api';

export function KillSwitchPanel() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ['trading', 'kill-switch'],
    queryFn: fetchKillSwitchEvents,
    refetchInterval: 10000,
  });

  const handleResolve = async (id: string) => {
    await fetch(`/api/v1/kill-switch/events/${id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: 'manual unlock from dashboard' }),
    });
    qc.invalidateQueries({ queryKey: ['trading', 'kill-switch'] });
  };

  if (!data) return null;
  const active = data.items.filter((e) => !e.resolved_at);

  return (
    <section className="p-4 border rounded">
      <h2 className="font-semibold mb-3">Kill Switch</h2>
      {active.length === 0 ? (
        <p className="text-green-600">All clear</p>
      ) : (
        <ul>
          {active.map((e) => (
            <li key={e.id} className="flex justify-between items-center border-b py-1">
              <span>
                {e.trigger_type}: {e.trigger_value} / {e.threshold}
              </span>
              <button
                onClick={() => handleResolve(e.id)}
                className="px-2 py-1 bg-red-500 text-white text-xs rounded"
              >
                Resolve
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
