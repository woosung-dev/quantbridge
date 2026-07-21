"use client";

// 온보딩 스텝 1: 환영 — C 디자인 언어 이식 (W3-E). 5분 내 첫 Pine 백테스트 안내.
// Bybit 데모 API 키 발급은 외부 가이드 링크로만 제공(실제 키 연결은 별도 트레이딩 플로우).

import { RocketIcon, ClockIcon, ExternalLinkIcon } from "lucide-react";

const BYBIT_DEMO_GUIDE_URL =
  "https://www.bybit.com/en/help-center/article/How-to-create-a-demo-trading-account";

export function Step1Welcome({ onNext }: { onNext: () => void }) {
  return (
    <div>
      <div className="ob-lede">
        <span className="ob-lede-icon" aria-hidden="true">
          <RocketIcon strokeWidth={1.8} />
        </span>
        <div>
          <h2 className="ob-heading">QuantBridge 에 오신 것을 환영합니다</h2>
          <p className="ob-subtle">
            5분 안에 첫 Pine Script 백테스트를 완주해보세요.
          </p>
        </div>
      </div>

      <ul className="ob-checklist">
        <li>
          <ClockIcon aria-hidden="true" strokeWidth={2} />
          <span className="break-keep">
            샘플 <strong>EMA Crossover</strong> 전략으로 시작하세요. 복사·붙여넣기
            없이 한 번의 클릭으로 등록됩니다.
          </span>
        </li>
        <li>
          <ClockIcon aria-hidden="true" strokeWidth={2} />
          <span className="break-keep">
            최근 30일 <strong>BTC/USDT 1H</strong> 캔들로 자동 백테스트가
            실행됩니다.
          </span>
        </li>
        <li>
          <ClockIcon aria-hidden="true" strokeWidth={2} />
          <span className="break-keep">
            총수익·승률·트레이드 수 등 핵심 지표를 즉시 확인합니다.
          </span>
        </li>
      </ul>

      <div className="ob-aside">
        <p className="ob-aside-label">선택. 실제 트레이딩을 원하시면.</p>
        <a
          href={BYBIT_DEMO_GUIDE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="ob-link"
        >
          Bybit 데모 계정 만드는 방법
          <ExternalLinkIcon aria-hidden="true" />
        </a>
        <p className="ob-aside-note">
          온보딩 이후 트레이딩 페이지에서 Bybit 데모 API 키를 등록할 수 있습니다.
        </p>
      </div>

      <div className="ob-actions end">
        <button
          className="btn btn-primary"
          type="button"
          onClick={onNext}
          aria-label="다음 단계로 진행"
        >
          시작하기
          <svg
            viewBox="0 0 24 24"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
    </div>
  );
}
