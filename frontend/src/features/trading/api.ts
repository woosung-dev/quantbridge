import { z } from 'zod';

export const OrderSchema = z.object({
  id: z.string().uuid(),
  symbol: z.string(),
  side: z.enum(['buy', 'sell']),
  state: z.enum(['pending', 'submitted', 'filled', 'rejected', 'cancelled']),
  quantity: z.string(),
  filled_price: z.string().nullable(),
  exchange_order_id: z.string().nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
});
export type Order = z.infer<typeof OrderSchema>;

export async function fetchOrders(limit = 50): Promise<{ items: Order[]; total: number }> {
  const res = await fetch(`/api/v1/orders?limit=${limit}&offset=0`);
  if (!res.ok) throw new Error('failed to fetch orders');
  const data = await res.json();
  return {
    items: z.array(OrderSchema).parse(data.items),
    total: data.total,
  };
}

// KillSwitchEvent — trigger_type corrected per ADR-006 CEO F4 rename
export const KillSwitchEventSchema = z.object({
  id: z.string().uuid(),
  trigger_type: z.enum(['cumulative_loss', 'daily_loss', 'api_error']),
  trigger_value: z.string(),
  threshold: z.string(),
  triggered_at: z.string(),
  resolved_at: z.string().nullable(),
});
export type KillSwitchEvent = z.infer<typeof KillSwitchEventSchema>;

export async function fetchKillSwitchEvents(): Promise<{ items: KillSwitchEvent[] }> {
  const res = await fetch('/api/v1/kill-switch/events?limit=20');
  if (!res.ok) throw new Error('failed to fetch kill switch events');
  const data = await res.json();
  return { items: z.array(KillSwitchEventSchema).parse(data.items) };
}

export const ExchangeAccountSchema = z.object({
  id: z.string().uuid(),
  exchange: z.string(),
  mode: z.string(),
  label: z.string().nullable(),
  api_key_masked: z.string(),
  created_at: z.string(),
});
export type ExchangeAccount = z.infer<typeof ExchangeAccountSchema>;

export async function fetchExchangeAccounts(): Promise<ExchangeAccount[]> {
  const res = await fetch('/api/v1/exchange-accounts');
  if (!res.ok) throw new Error('failed to fetch accounts');
  const data = await res.json();
  return z.array(ExchangeAccountSchema).parse(data.items);
}
