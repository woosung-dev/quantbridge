// 랜딩 히어로 (.lp-hero) — 2단: 소개 카피 + "화면 예시" 목업 리포트 카드.
// screen-14-landing.html 이식. 목업 숫자는 프로토타입 샘플임을 disclaimer 로 명시(정직성).
import Link from "next/link";

export function LandingHero() {
  return (
    <section className="lp-hero rise d1" aria-label="소개">
      <div>
        <div className="lp-hero-meta">
          <span className="chip">로컬 도구</span>
          <span className="chip">공개 전</span>
        </div>
        <h1 className="lp-hero-title">
          TradingView 전략을
          <br />
          가정까지 드러내서 검증합니다.
        </h1>
        <p className="lp-hero-sub">
          Pine Script 를 넣으면 먼저 파싱해서 무엇을 지원하고 무엇을 지원하지 않는지 알려 줍니다.
          그다음 봉을 하나씩 순회하는 백테스트로 체결과 비용을 재현하고, 최적화와 스트레스 테스트를
          거쳐 데모 계정에서 같은 코드 경로로 돌립니다.
        </p>
        <div className="lp-hero-cta">
          <Link className="btn btn-primary" href="/sign-up">
            시작하기
          </Link>
          <a className="btn btn-ghost" href="#support">
            지원 현황 확인
          </a>
        </div>
        <p className="lp-hero-fact">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="11" x2="12" y2="16" />
            <line x1="12" y1="7.5" x2="12.01" y2="7.5" />
          </svg>
          <span>
            현재 Bybit 데모 연동 기준으로 동작합니다. 공개 서비스가 아니라 개발자 한 사람이 로컬에서
            매일 쓰는 도구이고, 이 페이지는 언젠가 공개할 때 쓰려고 미리 적어 둔 초안입니다.
          </span>
        </p>
      </div>

      <div className="card">
        <div className="mock-head">
          <div>
            <p className="mock-title">백테스트 리포트</p>
            <p className="mock-sub">run_2f9c41 · BTC/USDT · 1h</p>
          </div>
          <span className="chip accent">화면 예시</span>
        </div>

        <div className="mock-chart">
          <svg
            viewBox="0 0 640 224"
            role="img"
            aria-label="자산 곡선 예시. 전략은 10,000 USDT 에서 22,740.18 USDT 로 끝나고, 같은 기간 매수 후 보유는 18,610.00 USDT 로 끝납니다."
          >
            <defs>
              <linearGradient id="lpEqFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--copper)" stopOpacity="0.18" />
                <stop offset="100%" stopColor="var(--copper)" stopOpacity="0" />
              </linearGradient>
            </defs>
            <g>
              <line className="grid-line" x1="56" y1="18" x2="624" y2="18" />
              <line className="grid-line" x1="56" y1="110" x2="624" y2="110" />
              <line className="axis-line" x1="56" y1="202" x2="624" y2="202" />
              <text className="axis-text" x="48" y="22" textAnchor="end">
                24,000
              </text>
              <text className="axis-text" x="48" y="114" textAnchor="end">
                16,000
              </text>
              <text className="axis-text" x="48" y="206" textAnchor="end">
                8,000
              </text>
            </g>
            <polygon
              fill="url(#lpEqFill)"
              points="56.0,179.0 70.2,176.7 84.4,180.1 98.6,174.4 112.8,169.8 127.0,164.1 141.2,166.3 155.4,157.1 169.6,151.4 183.8,154.9 198.0,146.8 212.2,138.7 226.4,142.2 240.6,149.1 254.8,143.3 269.0,134.1 283.2,126.1 297.4,130.7 311.6,120.3 325.8,112.3 340.0,118.1 354.2,138.7 368.4,130.7 382.6,119.2 396.8,104.3 411.0,96.2 425.2,100.8 439.4,91.6 453.6,82.4 467.8,87.0 482.0,97.3 496.2,88.1 510.4,77.8 524.6,68.6 538.8,74.3 553.0,61.7 567.2,52.5 581.4,58.3 595.6,47.9 609.8,39.9 624.0,32.5 624,202 56,202"
            />
            <polyline
              className="bm-line"
              points="56.0,179.0 70.2,172.1 84.4,162.9 98.6,169.8 112.8,157.1 127.0,146.8 141.2,156.0 155.4,139.9 169.6,130.7 183.8,143.3 198.0,151.4 212.2,137.6 226.4,123.8 240.6,134.1 254.8,145.7 269.0,131.9 283.2,116.9 297.4,126.1 311.6,138.7 325.8,122.7 340.0,107.7 354.2,120.3 368.4,135.3 382.6,121.5 396.8,105.4 411.0,92.7 425.2,107.7 439.4,121.5 453.6,106.5 467.8,89.3 482.0,103.1 496.2,116.9 510.4,99.7 524.6,84.7 538.8,98.5 553.0,111.1 567.2,93.9 581.4,76.7 595.6,91.6 609.8,85.9 624.0,79.7"
            />
            <polyline
              className="eq-line"
              points="56.0,179.0 70.2,176.7 84.4,180.1 98.6,174.4 112.8,169.8 127.0,164.1 141.2,166.3 155.4,157.1 169.6,151.4 183.8,154.9 198.0,146.8 212.2,138.7 226.4,142.2 240.6,149.1 254.8,143.3 269.0,134.1 283.2,126.1 297.4,130.7 311.6,120.3 325.8,112.3 340.0,118.1 354.2,138.7 368.4,130.7 382.6,119.2 396.8,104.3 411.0,96.2 425.2,100.8 439.4,91.6 453.6,82.4 467.8,87.0 482.0,97.3 496.2,88.1 510.4,77.8 524.6,68.6 538.8,74.3 553.0,61.7 567.2,52.5 581.4,58.3 595.6,47.9 609.8,39.9 624.0,32.5"
            />
            <circle cx="624" cy="32.5" r="3.2" fill="var(--copper)" />
            <g>
              <text className="axis-text" x="56" y="218" textAnchor="start">
                2024-01
              </text>
              <text className="axis-text" x="340" y="218" textAnchor="middle">
                2025-02
              </text>
              <text className="axis-text" x="624" y="218" textAnchor="end">
                2026-04
              </text>
            </g>
          </svg>
        </div>

        <div className="mock-stats">
          <div className="mock-stat">
            <p className="mock-k">총 수익률</p>
            <p className="mock-v pos">+127.40%</p>
          </div>
          <div className="mock-stat">
            <p className="mock-k">매수 후 보유</p>
            <p className="mock-v">+86.10%</p>
          </div>
          <div className="mock-stat">
            <p className="mock-k">최대 낙폭</p>
            <p className="mock-v neg">-14.60%</p>
          </div>
        </div>

        <p className="disclaimer">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 3 2.5 20h19L12 3z" />
            <line x1="12" y1="10" x2="12" y2="14" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          이 화면 예시의 숫자는 프로토타입용 샘플 데이터입니다. 실제 계좌의 성과가 아닙니다.
        </p>
      </div>
    </section>
  );
}
