// 503 점검 페이지 — screen-13 §03(503) 의 C 언어 구조 이식(W3-H). 앱 셸 밖(app 루트)이라
// 공용 .page 컨테이너로 단독 렌더한다. 정적 라우트라 예상 복구 시각·마지막 성공 응답 같은
// 라이브 값은 지어내지 않는다(§4.9). 예상 복구 시간은 서버가 주지 않으므로 무데이터 셀로 둔다.
// 재시도 권장 간격 30초(Retry-After)는 HTTP 재시도 정책이며 트레이딩 주문 재시도(3회 · 지수
// 백오프)와 다른 개념이라 섞지 않는다(§4.7). page 는 서버 컴포넌트로 유지하고 재시도 버튼만
// 말단 클라이언트 컴포넌트로 분리한다.

import Link from "next/link";
import { HomeIcon, PowerIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { InfoIcon } from "@/components/info-icon";
import { EMPTY_CELL } from "@/lib/labels";
import { MaintenanceRetryButton } from "@/components/maintenance-retry-button";

export default function MaintenancePage() {
  return (
    <main className="page">
      <section className="section" aria-labelledby="err-503-heading">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">503</span> 사용 불가
          </p>
          <h1 id="err-503-heading" className="section-title">
            서비스를 일시적으로 사용할 수 없습니다.
          </h1>
          <p className="section-desc">
            예상 복구 시간과 진행률은 인쇄하지 않습니다. 서버가 주지 않은 값이기 때문입니다. 아는 사실만
            표에 남깁니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h2 className="card-title">헬스 체크 응답 없음</h2>
              <p className="card-sub">백엔드가 요청을 받지 못하는 상태입니다.</p>
            </div>
            <span className="chip">503</span>
          </div>

          <div className="card-body">
            <StateBox
              tone="failed"
              className="err-hero"
              testId="maintenance-503-state"
              icon={<PowerIcon aria-hidden="true" />}
              title="서버가 요청을 받지 못하는 상태입니다."
              body="배포나 점검 중일 수도 있고 프로세스가 내려가 있을 수도 있습니다. 이 화면은 둘 중 무엇인지 알지 못합니다."
              code="GET /health · 503"
            />
          </div>

          <div className="trust-grid">
            <div className="trust-col">
              <div className="trust-row">
                <span className="trust-key">상태 코드</span>
                <span className="trust-val">503</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">엔드포인트</span>
                <span className="trust-val">GET /health</span>
              </div>
            </div>
            <div className="trust-col">
              <div className="trust-row">
                <span className="trust-key">재시도 권장 간격</span>
                <span className="trust-val">30초 · Retry-After 헤더 값</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">예상 복구 시간</span>
                <span className="trust-val empty" title="서버가 복구 예정 시각을 제공하지 않습니다.">
                  {EMPTY_CELL}
                </span>
              </div>
              <div className="trust-row">
                <span className="trust-key">자동 재시도</span>
                <span className="trust-val">없음 · 버튼을 눌러야 재시도</span>
              </div>
            </div>
          </div>

          <p className="chart-note">
            <InfoIcon />
            복구 예정 시각을 표시하지 않는 이유는 서버가 그 값을 주지 않기 때문입니다. 추정치를 시간
            약속처럼 보이게 하지 않습니다.
          </p>

          <div className="err-actions" role="group" aria-label="복구 동작">
            <MaintenanceRetryButton />
            <Link className="btn" href="/">
              <HomeIcon aria-hidden="true" />
              홈으로
            </Link>
          </div>

          <p className="disclaimer">
            <InfoIcon />
            <span>
              이 화면은 상태를 자동으로 갱신하지 않습니다. 복구 여부는 다시 시도 버튼으로만 확인하며,
              그래서 맥동 점 · 진행률 바 · 카운트다운을 넣지 않았습니다.
            </span>
          </p>
        </div>
      </section>
    </main>
  );
}
