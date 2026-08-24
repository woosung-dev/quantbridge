// 웨이트리스트 히어로 좌측 카피 (.hero-copy) — 소개 + 칩 + 사실 카드. screen-17-waitlist.html 이식.
// 공개 시점·가격은 미정(무데이터 + title). 대기자 수·순번은 집계하지 않으므로 표시하지 않는다.
export function WaitlistHero() {
  return (
    <div className="hero-copy">
      <h1 className="hero-title">
        TradingView Pine 전략을 백테스트하고, 같은 전략을 거래소에 연결합니다.
      </h1>
      <p className="hero-sub">
        지금은 개발자 본인이 매일 사용하며 검증하는 단계입니다. 공개 시점은 정하지 않았습니다.
        준비가 시작되면 등록하신 주소로 알리겠습니다.
      </p>

      <div className="hero-chips">
        <span className="chip">바 단위 이벤트 루프 자체 인터프리터</span>
        <span className="chip">Bybit 데모</span>
      </div>

      <div className="card hero-facts">
        <div className="trust-col">
          <div className="trust-row">
            <span className="trust-key">현재 단계</span>
            <span className="trust-val">개발자 1인 로컬 사용</span>
          </div>
          <div className="trust-row">
            <span className="trust-key">공개 시점</span>
            <span className="trust-val dim" title="공개 일정을 아직 정하지 않았습니다.">
              미정
            </span>
          </div>
          <div className="trust-row">
            <span className="trust-key">가격</span>
            <span className="trust-val dim" title="가격 정책을 아직 정하지 않았습니다.">
              미정
            </span>
          </div>
          <div className="trust-row">
            <span className="trust-key">보낼 메일</span>
            <span className="trust-val">공개 안내 1회</span>
          </div>
        </div>
      </div>
    </div>
  );
}
