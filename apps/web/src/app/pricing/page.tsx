// 요금제 페이지 (/pricing) — C 디자인 언어 이식. screen-16-pricing.html.
// 가격은 미정이라 비워 두고, 지금 무엇이 되고 무엇이 안 되는지를 그대로 적는다(§4.8 정직성).
// OKX/Binance/Bitget 은 로드맵으로만 표기(§4.8). 공개 판매 전 · 사용자 1명.
import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";

import { EMPTY_CELL } from "@/lib/marketing-canon";

import { PricingWaitlistForm } from "@/features/marketing/components/pricing-waitlist-form";

export const metadata: Metadata = {
  title: "요금제",
  description:
    "QuantBridge 요금제. 아직 가격을 정하지 않았고, 지금 무엇이 되고 무엇이 안 되는지를 그대로 적었습니다.",
};

const CHECK = (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const MINUS = (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

function FeatOn({ children }: { children: ReactNode }) {
  return (
    <p className="feat on">
      {CHECK}
      {children}
    </p>
  );
}
function FeatOff({ children }: { children: ReactNode }) {
  return (
    <p className="feat off">
      {MINUS}
      {children}
    </p>
  );
}

interface CmpRow {
  label: string;
  cells: [ReactNode, ReactNode, ReactNode];
}

const NO_LOCAL = "로컬 구성에서는 계획에 없습니다.";
const NO_CLOUD = "클라우드 구성에 포함할지 아직 정하지 않았습니다.";
const NO_PAY_LOCAL = "로컬 실행에는 결제 경로가 필요하지 않습니다.";
const NO_PAY = "결제 수단과 가격을 아직 정하지 않았습니다.";

const yes = <td className="val yes">지원</td>;
const road = <td className="val">로드맵</td>;
const empty = (title: string) => (
  <td className="val" title={title}>
    {EMPTY_CELL}
  </td>
);

const CMP_ROWS: CmpRow[] = [
  { label: "Pine Script 파싱", cells: [yes, road, road] },
  { label: "자체 인터프리터 백테스트 (바 단위 이벤트 루프)", cells: [yes, road, road] },
  { label: "파라미터 최적화 (그리드 · 베이지안 · 유전)", cells: [yes, road, road] },
  { label: "스트레스 테스트 (몬테카를로 · 워크포워드)", cells: [yes, road, road] },
  { label: "Bybit 데모 트레이딩", cells: [yes, road, road] },
  { label: "Kill Switch (신규 주문 차단)", cells: [yes, road, road] },
  { label: "OKX · Binance · Bitget 연동", cells: [road, road, road] },
  { label: "클라우드 실행", cells: [empty(NO_LOCAL), road, road] },
  { label: "다중 사용자 계정", cells: [empty(NO_LOCAL), empty(NO_CLOUD), road] },
  { label: "팀 전략 공유", cells: [empty(NO_LOCAL), empty(NO_CLOUD), road] },
  { label: "결제 · 청구", cells: [empty(NO_PAY_LOCAL), empty(NO_PAY), empty(NO_PAY)] },
];

const PRICE_UNSET_TITLE = "아직 정하지 않았습니다.";

const PRICING_FAQ: { q: string; a: string }[] = [
  {
    q: "언제 판매하나요?",
    a: "정해진 날짜가 없습니다. 결제, 다중 사용자 계정, 클라우드 실행 세 가지가 모두 붙기 전에는 팔지 않습니다. 셋 다 지금은 코드에 없습니다. 웨이트리스트에 등록하면 판매를 시작할 때 한 번 알립니다.",
  },
  {
    q: "지금 쓸 수 있나요?",
    a: "개발자 본인의 로컬 환경에서만 돕니다. 가입 경로가 없고, 접속할 수 있는 주소도 없습니다. 저장소를 직접 받아 도커로 띄우면 백테스트와 데모 트레이딩까지 동작하지만, 설치 문서와 지원은 아직 준비하지 않았습니다.",
  },
  {
    q: "데이터는 어디에 저장되나요?",
    a: "실행하는 컴퓨터 안의 PostgreSQL (TimescaleDB) 와 Redis 에만 저장됩니다. 외부로 나가는 통신은 거래소 API 호출과 시세 수집뿐이고, 분석 도구나 광고 스크립트는 붙어 있지 않습니다. 거래소 API 키는 AES-256 (Fernet) 으로 암호화해 저장합니다.",
  },
  {
    q: "라이브 거래는 얼마나 위험한가요?",
    a: "백테스트 결과는 미래 수익을 보장하지 않습니다. 라이브 주문은 실제 자금을 움직이고 손실은 사용자 책임입니다. 먼저 데모 세션으로 검증하기를 권합니다. Kill Switch 는 신규 주문을 막을 뿐, 이미 열려 있는 포지션을 자동으로 청산하지는 않습니다.",
  },
];

function CmpCell({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export default function PricingPage() {
  return (
    <div className="pricing-page">
      <header className="site-head">
        <div className="site-head-in">
          <Link className="site-brand" href="/" aria-label="QuantBridge 홈으로">
            <span className="brand-mark" aria-hidden="true">
              <svg
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

          <nav className="site-nav" aria-label="이 페이지의 목차">
            <a href="#plans">계획 중인 구성</a>
            <a href="#compare">항목별 비교</a>
            <a href="#faq">자주 묻는 질문</a>
          </nav>

          <span className="head-spacer" />

          <a className="btn" href="#waitlist" aria-label="웨이트리스트 등록">
            <span className="cta-long">웨이트리스트 등록</span>
            <span className="cta-short" aria-hidden="true">
              등록
            </span>
          </a>
        </div>
      </header>

      <main className="site-main" id="main-content">
        <div className="page">
          {/* 히어로 */}
          <section className="hero-text rise d1" aria-label="요금제 개요">
            <h1>요금제</h1>
            <p>
              아직 가격이 없습니다. 정하지 않았기 때문에 비워 두었고, 대신 지금 무엇이 되고 무엇이
              안 되는지를 그대로 적었습니다.
            </p>
            <div className="hero-meta">
              <span className="chip">공개 판매 전</span>
              <span className="chip">사용자 1명 (woosung)</span>
              <span className="chip accent">바 단위 이벤트 루프 자체 인터프리터</span>
            </div>
          </section>

          {/* 01 현재 상태 */}
          <section className="section rise d2" aria-label="현재 상태">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">01</span> 현재 상태
              </p>
              <h2 className="section-title">지금 이 제품이 서 있는 자리</h2>
              <p className="section-desc">판매 여부와 사용 가능 범위를 먼저 밝힙니다.</p>
            </header>

            <div className="card">
              <div className="notice-card">
                <span className="state-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="9" />
                    <line x1="12" y1="8" x2="12" y2="13" />
                    <line x1="12" y1="16.4" x2="12" y2="16.5" />
                  </svg>
                </span>
                <div>
                  <h3 className="notice-card-title">현재 QuantBridge 는 공개 판매하지 않습니다.</h3>
                  <p className="notice-card-body">
                    개발자 본인의 로컬 워크스페이스에서 매일 사용하며 검증하는 단계입니다. 계정도
                    결제도 열려 있지 않고, 서버에 올라간 인스턴스도 없습니다. 아래 세 구성은
                    만들겠다고 정한 계획이며, 가격은 아직 정하지 않았습니다.
                  </p>
                  <div className="notice-card-actions">
                    <a className="btn btn-primary" href="#waitlist">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M4 6h16v12H4z" />
                        <polyline points="4 7 12 13 20 7" />
                      </svg>
                      웨이트리스트 등록
                    </a>
                    <Link className="btn btn-ghost" href="/sign-up">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <line x1="6" y1="20" x2="6" y2="14" />
                        <line x1="12" y1="20" x2="12" y2="4" />
                        <line x1="18" y1="20" x2="18" y2="10" />
                      </svg>
                      무엇을 검증했는지 보기
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 02 계획 중인 구성 */}
          <section className="section rise d3" id="plans" aria-label="계획 중인 구성">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">02</span> 계획 중인 구성
              </p>
              <h2 className="section-title">세 가지 구성을 계획하고 있습니다</h2>
              <p className="section-desc">
                각 구성에서 지금 실제로 도는 기능과 아직 못 도는 기능을 나눠 적었습니다. 가격 칸은
                정하지 않아 비워 두었습니다.
              </p>
            </header>

            <div className="plan-row">
              {/* 로컬 */}
              <article className="card plan">
                <div className="plan-top">
                  <div className="report-meta" style={{ marginTop: 0 }}>
                    <span className="chip done">
                      {CHECK}
                      지금 도는 구성
                    </span>
                  </div>
                  <h3 className="plan-name" style={{ marginTop: 10 }}>
                    로컬
                  </h3>
                  <p className="plan-for">
                    저장소를 받아 자기 컴퓨터에서 도커로 직접 띄우는 방식입니다.
                  </p>
                  <p className="plan-price">
                    <span className="amt mono" title={PRICE_UNSET_TITLE}>
                      {EMPTY_CELL}
                    </span>
                    <span className="unit">가격을 아직 정하지 않았습니다.</span>
                  </p>
                  <p className="plan-meter-foot">
                    아래 비교표 11개 중 로컬에 해당하는 <span className="mono">7</span>개 기준으로
                    지금 되는 것 <span className="mono">6</span>개 (85.7%). 로컬 계획에 없는 4개
                    항목은 분모에서 뺐습니다.
                  </p>
                </div>
                <div className="plan-body">
                  <div>
                    <p className="plan-sub">지금 되는 것</p>
                    <div className="feat-list">
                      <FeatOn>Pine Script 파싱</FeatOn>
                      <FeatOn>자체 인터프리터 백테스트 (바 단위 이벤트 루프)</FeatOn>
                      <FeatOn>파라미터 최적화 (그리드 9조합, 베이지안 100회, 유전 100회)</FeatOn>
                      <FeatOn>스트레스 테스트</FeatOn>
                      <FeatOn>Bybit 데모 트레이딩</FeatOn>
                      <FeatOn>Kill Switch (신규 주문 차단)</FeatOn>
                    </div>
                  </div>
                  <div>
                    <p className="plan-sub">아직 아닌 것</p>
                    <div className="feat-list">
                      <FeatOff>
                        설치 문서와 사용자 지원<span className="chip">로드맵</span>
                      </FeatOff>
                      <FeatOff>
                        OKX · Binance · Bitget 연동
                        <span className="chip">로드맵</span>
                      </FeatOff>
                      <FeatOff>결제. 로컬 실행에는 결제 경로 자체가 없습니다.</FeatOff>
                    </div>
                  </div>
                  <Link className="btn btn-ghost btn-block" href="/sign-up">
                    로컬에서 도는 화면 보기
                  </Link>
                </div>
              </article>

              {/* 클라우드 */}
              <article className="card plan">
                <div className="plan-top">
                  <div className="report-meta" style={{ marginTop: 0 }}>
                    <span className="chip">계획</span>
                  </div>
                  <h3 className="plan-name" style={{ marginTop: 10 }}>
                    클라우드
                  </h3>
                  <p className="plan-for">
                    백테스트와 세션을 내 컴퓨터가 꺼져 있어도 돌리는 방식입니다.
                  </p>
                  <p className="plan-price">
                    <span className="amt mono" title={PRICE_UNSET_TITLE}>
                      {EMPTY_CELL}
                    </span>
                    <span className="unit">가격을 아직 정하지 않았습니다.</span>
                  </p>
                  <p className="plan-meter-foot">
                    아래 비교표 11개 중 클라우드에 해당하는 <span className="mono">8</span>개
                    기준으로 지금 되는 것 <span className="mono">0</span>개 (0%). 포함 여부를 정하지
                    않은 3개 항목은 분모에서 뺐습니다.
                  </p>
                </div>
                <div className="plan-body">
                  <div>
                    <p className="plan-sub">지금 되는 것</p>
                    <div className="feat-list">
                      <FeatOff>없습니다. 배포된 인스턴스가 아직 하나도 없습니다.</FeatOff>
                    </div>
                  </div>
                  <div>
                    <p className="plan-sub">만들려는 것</p>
                    <div className="feat-list">
                      <FeatOff>
                        클라우드에서 백테스트 · 최적화 실행
                        <span className="chip">로드맵</span>
                      </FeatOff>
                      <FeatOff>
                        내 컴퓨터와 무관하게 유지되는 데모 세션
                        <span className="chip">로드맵</span>
                      </FeatOff>
                      <FeatOff>
                        결제와 청구<span className="chip">로드맵</span>
                      </FeatOff>
                    </div>
                  </div>
                  <button
                    className="btn btn-ghost btn-block"
                    type="button"
                    disabled
                    aria-disabled="true"
                  >
                    아직 열 수 없습니다
                  </button>
                </div>
              </article>

              {/* 팀 */}
              <article className="card plan">
                <div className="plan-top">
                  <div className="report-meta" style={{ marginTop: 0 }}>
                    <span className="chip">계획</span>
                  </div>
                  <h3 className="plan-name" style={{ marginTop: 10 }}>
                    팀
                  </h3>
                  <p className="plan-for">전략과 실행 기록을 여러 사람이 함께 보는 방식입니다.</p>
                  <p className="plan-price">
                    <span className="amt mono" title={PRICE_UNSET_TITLE}>
                      {EMPTY_CELL}
                    </span>
                    <span className="unit">가격을 아직 정하지 않았습니다.</span>
                  </p>
                  <p className="plan-meter-foot">
                    아래 비교표 11개 중 팀에 해당하는 <span className="mono">10</span>개 기준으로
                    지금 되는 것 <span className="mono">0</span>개 (0%). 결제는 가격을 정하지 않아
                    분모에서 뺐습니다.
                  </p>
                </div>
                <div className="plan-body">
                  <div>
                    <p className="plan-sub">지금 되는 것</p>
                    <div className="feat-list">
                      <FeatOff>없습니다. 지금은 계정 하나로만 검증했습니다.</FeatOff>
                    </div>
                  </div>
                  <div>
                    <p className="plan-sub">만들려는 것</p>
                    <div className="feat-list">
                      <FeatOff>
                        다중 사용자 계정<span className="chip">로드맵</span>
                      </FeatOff>
                      <FeatOff>
                        팀 안에서 전략과 리포트 공유
                        <span className="chip">로드맵</span>
                      </FeatOff>
                      <FeatOff>
                        역할별 권한 분리<span className="chip">로드맵</span>
                      </FeatOff>
                    </div>
                  </div>
                  <button
                    className="btn btn-ghost btn-block"
                    type="button"
                    disabled
                    aria-disabled="true"
                  >
                    아직 열 수 없습니다
                  </button>
                </div>
              </article>
            </div>
          </section>

          {/* 03 항목별 비교 */}
          <section className="section rise d4" id="compare" aria-label="항목별 비교">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">03</span> 항목별 비교
              </p>
              <h2 className="section-title">구성별로 지금 무엇이 되는지</h2>
              <p className="section-desc">
                확인한 것만 지원으로 적었습니다. 결정하지 않은 칸은 비워 두었습니다.
              </p>
            </header>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">기능 대조표</h3>
                  <p className="card-sub">비교 항목 11개 · 그중 지원으로 확인한 것 6개</p>
                </div>
                <div className="report-meta" style={{ marginTop: 0 }}>
                  <span className="chip accent">가격 미정</span>
                </div>
              </div>

              <div className="table-wrap">
                <table className="trades cmp" aria-label="구성별 기능 대조표">
                  <thead>
                    <tr>
                      <th scope="col">기능</th>
                      <th scope="col" className="val">
                        로컬
                      </th>
                      <th scope="col" className="val">
                        클라우드
                      </th>
                      <th scope="col" className="val">
                        팀
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {CMP_ROWS.map((row, i) => (
                      <tr key={i}>
                        <td className="row-label">{row.label}</td>
                        {row.cells.map((cell, j) => (
                          <CmpCell key={j}>{cell}</CmpCell>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="chart-note">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="9" />
                  <line x1="12" y1="11" x2="12" y2="16" />
                  <line x1="12" y1="7.6" x2="12" y2="7.7" />
                </svg>
                연결해 본 거래소는 Bybit (데모 · 메인넷) 하나입니다. OKX 와 Binance 와 Bitget 은
                로드맵이며 아직 연결하지 않았습니다.
              </p>

              <p className="disclaimer">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M12 3 3 20h18z" />
                  <line x1="12" y1="10" x2="12" y2="14.5" />
                  <line x1="12" y1="17" x2="12" y2="17.1" />
                </svg>
                <span>
                  이 표에 가격은 없습니다. 세 구성 모두 금액을 정하지 않았고, 비어 있는 칸은 임의로
                  채우는 대신 그대로 두었습니다. 지원으로 적은 6개 항목은 로컬 워크스페이스에서
                  실제로 실행해 본 기능입니다.
                </span>
              </p>
            </div>
          </section>

          {/* 04 FAQ */}
          <section className="section rise d5" id="faq" aria-label="자주 묻는 질문">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">04</span> 자주 묻는 질문
              </p>
              <h2 className="section-title">먼저 답해 두는 네 가지</h2>
              <p className="section-desc">
                판매 시점, 사용 가능 여부, 데이터 위치, 라이브 거래 위험을 밝힙니다.
              </p>
            </header>

            <div className="faq-list">
              {PRICING_FAQ.map((f) => (
                <article key={f.q} className="card card-pad">
                  <h3 className="faq-q">{f.q}</h3>
                  <p className="faq-a">{f.a}</p>
                </article>
              ))}
            </div>
          </section>

          {/* 05 웨이트리스트 */}
          <section className="section rise d6" id="waitlist" aria-label="웨이트리스트 등록">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">05</span> 웨이트리스트
              </p>
              <h2 className="section-title">판매를 시작하면 한 번 알립니다</h2>
              <p className="section-desc">
                등록 인원수나 대기 순번은 세지 않습니다. 보낼 메일도 그 한 통뿐입니다.
              </p>
            </header>

            <PricingWaitlistForm />
          </section>
        </div>

        <footer className="site-foot">
          <div className="site-foot-in">
            <div>
              <span className="site-brand">
                <span className="brand-mark" aria-hidden="true">
                  <svg
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
              </span>
              <p className="foot-note" style={{ marginTop: 10 }}>
                Pine Script 전략을 백테스트하고 데모로 검증하는 개인 워크스페이스입니다.
                <br />
                공개 판매하지 않습니다.
              </p>
            </div>

            <nav className="foot-links" aria-label="푸터 링크">
              <a href="#plans">계획 중인 구성</a>
              <a href="#compare">항목별 비교</a>
              <a href="#faq">자주 묻는 질문</a>
              <a href="#waitlist">웨이트리스트</a>
              <Link href="/">홈</Link>
            </nav>
          </div>
        </footer>
      </main>
    </div>
  );
}
