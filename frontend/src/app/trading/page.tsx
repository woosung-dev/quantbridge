import { OrdersPanel } from '@/features/trading/OrdersPanel';
import { KillSwitchPanel } from '@/features/trading/KillSwitchPanel';
import { ExchangeAccountsPanel } from '@/features/trading/ExchangeAccountsPanel';

export default function TradingPage() {
  return (
    <main className="p-6 space-y-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold">Trading</h1>
      <KillSwitchPanel />
      <OrdersPanel />
      <ExchangeAccountsPanel />
    </main>
  );
}
