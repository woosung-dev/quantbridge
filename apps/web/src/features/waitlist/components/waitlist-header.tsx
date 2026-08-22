// 웨이트리스트 자체 헤더 (.mkt-head) — 브랜드 + 앵커 메뉴 + 등록 폼 이동 + 테마 토글.
// screen-17-waitlist.html 이식. 프로토타입의 가짜 토스트 토글은 실 ThemeToggle 로 대체.
import Link from "next/link";

import { ThemeToggle } from "@/components/ui/theme-toggle";

export function WaitlistHeader() {
  return (
    <header className="mkt-head">
      <div className="mkt-head-inner">
        <Link className="mkt-brand" href="/" aria-label="QuantBridge 홈으로">
          <span className="brand-mark" aria-hidden="true">
            <svg
              aria-hidden="true"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="3 17 9 11 13 15 21 7" />
              <polyline points="15 7 21 7 21 13" />
            </svg>
          </span>
          <span className="brand-name">QuantBridge</span>
        </Link>

        <span className="mkt-spacer" />

        <nav className="mkt-nav" aria-label="페이지 안 이동">
          <a className="mkt-link" href="#build">
            무엇을 만들고 있나
          </a>
          <a className="mkt-link" href="#support">
            지원 현황
          </a>
          <a className="mkt-link" href="#faq">
            FAQ
          </a>
        </nav>

        <a className="btn btn-ghost" href="#signup">
          등록 폼으로
        </a>

        <ThemeToggle />
      </div>
    </header>
  );
}
