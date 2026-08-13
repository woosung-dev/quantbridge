// 404 not-found 페이지 — screen-13 §01 의 C 언어 구조 이식(W3-H). 앱 셸 밖(app 루트)이라
// 공용 .page 컨테이너로 단독 렌더한다. 특정 실행 ID 를 모르는 제네릭 404 라 프로토타입의
// run_ffffff · GET 경로 같은 컨텍스트 값은 인쇄하지 않는다(§4.9 스키마 미보증 값 미렌더).

import type { ReactNode } from "react";
import Link from "next/link";
import { BarChart3Icon, CodeIcon, LayoutDashboardIcon, SearchXIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { InfoIcon } from "@/components/info-icon";

// 복구 경로 — 이 워크스페이스에 실제로 존재하는 라우트로만 연결한다(동작하지 않는 링크 금지).
interface RecoveryRoute {
  href: string;
  title: string;
  desc: string;
  cta: string;
  icon: ReactNode;
  recommended?: boolean;
}

const RECOVERY_ROUTES: readonly RecoveryRoute[] = [
  {
    href: "/backtests",
    title: "백테스트 목록",
    desc: "이 워크스페이스에 저장된 실행을 최근 순으로 봅니다. 찾던 실행이 남아 있다면 여기에 있습니다.",
    cta: "백테스트 목록 열기",
    icon: <BarChart3Icon aria-hidden="true" />,
    recommended: true,
  },
  {
    href: "/strategies",
    title: "전략 목록",
    desc: "실행이 아니라 전략을 찾고 있었다면 전략 목록에서 다시 실행을 걸 수 있습니다.",
    cta: "전략 목록 열기",
    icon: <CodeIcon aria-hidden="true" />,
  },
  {
    href: "/dashboard",
    title: "대시보드",
    desc: "어디로 갈지 모르겠다면 워크스페이스 첫 화면으로 돌아갑니다.",
    cta: "대시보드 열기",
    icon: <LayoutDashboardIcon aria-hidden="true" />,
  },
];

export default function NotFound() {
  return (
    <main className="page">
      <section className="section" aria-labelledby="err-404-heading">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">404</span> 찾을 수 없음
          </p>
          <h1 id="err-404-heading" className="section-title">
            요청한 페이지를 찾을 수 없습니다.
          </h1>
          <p className="section-desc">
            주소가 삭제되었거나 처음부터 없었던 경우입니다. 서버는 이 둘을 구분해 주지 않으므로 화면도
            구분하지 않습니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h2 className="card-title">페이지 조회 실패</h2>
              <p className="card-sub">요청한 주소에서 화면을 열지 못했습니다.</p>
            </div>
            <span className="chip">404</span>
          </div>

          <div className="card-body">
            <StateBox
              className="err-hero"
              testId="not-found-state"
              icon={<SearchXIcon aria-hidden="true" />}
              title="요청한 주소를 이 워크스페이스에서 찾을 수 없습니다."
              body="삭제되었거나 처음부터 존재하지 않은 주소입니다. 직접 입력했다면 오타를 확인하고, 링크를 따라왔다면 아래 목록에서 다시 찾는 편이 빠릅니다."
            />
          </div>

          <p className="chart-note">
            <InfoIcon />
            아래 카드 세 곳은 이 워크스페이스에 실제로 존재하는 경로로 연결됩니다. 동작하지 않는 검색창과
            빈 링크는 그리지 않습니다.
          </p>
        </div>

        <div className="cta-row" data-testid="not-found-cta-row" style={{ marginTop: 16 }}>
          {RECOVERY_ROUTES.map((route) => (
            <article
              key={route.href}
              className={route.recommended ? "card cta recommended" : "card cta"}
            >
              {route.recommended ? <span className="cta-badge">권장</span> : null}
              <span className="cta-icon" aria-hidden="true">
                {route.icon}
              </span>
              <h3 className="cta-title">{route.title}</h3>
              <p className="cta-desc">{route.desc}</p>
              <p className="cta-meta">{route.href}</p>
              <Link
                className={route.recommended ? "btn btn-primary btn-block" : "btn btn-block"}
                href={route.href}
              >
                {route.cta}
              </Link>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
