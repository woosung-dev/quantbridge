"use client";

// H2 Sprint 11 Phase D Step 1: Welcome — 5분 내 Pine 첫 백테스트 안내.
// Bybit Demo API 키 발급은 외부 가이드 링크로만 제공 (실제 키 연결은 별도 Trading 플로우).

import { RocketIcon, ClockIcon, ExternalLinkIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

const BYBIT_DEMO_GUIDE_URL =
  "https://www.bybit.com/en/help-center/article/How-to-create-a-demo-trading-account";

export function Step1Welcome({ onNext }: { onNext: () => void }) {
  return (
    <div>
      <div className="mb-5 flex items-center gap-3">
        <div className="grid size-12 place-items-center rounded-full bg-[color:var(--primary-light)]">
          <RocketIcon
            className="size-6 text-[color:var(--primary)]"
            strokeWidth={1.8}
          />
        </div>
        <div>
          <h2 className="font-display text-xl font-bold">QuantBridge 에 오신 것을 환영합니다</h2>
          <p className="text-xs text-[color:var(--text-muted)]">
            5분 안에 첫 Pine Script 백테스트를 완주해보세요.
          </p>
        </div>
      </div>

      <ul className="mb-6 space-y-3 text-sm text-[color:var(--text-secondary)]">
        <li className="flex items-start gap-3">
          <ClockIcon
            className="mt-0.5 size-4 shrink-0 text-[color:var(--primary)]"
            strokeWidth={2}
          />
          <span className="break-keep">
            샘플 <strong>EMA Crossover</strong> 전략으로 시작 — 복사·붙여넣기 없이 한 번의 클릭으로 등록됩니다.
          </span>
        </li>
        <li className="flex items-start gap-3">
          <ClockIcon
            className="mt-0.5 size-4 shrink-0 text-[color:var(--primary)]"
            strokeWidth={2}
          />
          <span className="break-keep">
            최근 30일 <strong>BTC/USDT 1H</strong> 캔들로 자동 백테스트가 실행됩니다.
          </span>
        </li>
        <li className="flex items-start gap-3">
          <ClockIcon
            className="mt-0.5 size-4 shrink-0 text-[color:var(--primary)]"
            strokeWidth={2}
          />
          <span className="break-keep">
            총수익·승률·트레이드 수 등 핵심 지표를 즉시 확인합니다.
          </span>
        </li>
      </ul>

      <div className="mb-6 rounded-[var(--radius-md)] border border-dashed border-[color:var(--border)] bg-[color:var(--bg-alt)] p-4">
        <p className="mb-2 text-xs font-semibold text-[color:var(--text-secondary)]">
          선택: 실제 트레이딩을 원하시면
        </p>
        <a
          href={BYBIT_DEMO_GUIDE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-[color:var(--primary)] underline-offset-2 hover:underline"
        >
          Bybit Demo Trading 계정 만드는 방법
          <ExternalLinkIcon className="size-3" />
        </a>
        <p className="mt-2 text-[0.7rem] text-[color:var(--text-muted)] break-keep">
          온보딩 이후 Trading 페이지에서 Demo API 키를 등록할 수 있습니다.
        </p>
      </div>

      <div className="flex justify-end">
        <Button onClick={onNext} aria-label="다음 단계로 진행">
          시작하기 →
        </Button>
      </div>
    </div>
  );
}
