// 인증 화면 좌측 브랜드 패널 (.auth-brand) — C 디자인 언어. screen-15-login.html 이식.
// 확인 가능한 사실 4가지만 적는다. 가공 인물·후기·가짜 라이브 점·아바타 군집은 쓰지 않는다(C7·C14).
// mode 무관 — 좌 패널은 제품 사실이라 로그인/회원가입에서 동일하다.

interface Fact {
  idx: string;
  title: React.ReactNode;
  body: string;
}

const FACTS: Fact[] = [
  {
    idx: "01",
    title: "엔진은 바 단위 이벤트 루프 자체 인터프리터입니다.",
    body: "봉을 하나씩 순회하며 실행합니다. 지표를 미리 다 계산해 두고 한 번에 훑는 방식이 아니라, 봉마다 주문과 잔고 상태를 다시 계산합니다.",
  },
  {
    idx: "02",
    title: "거래소 API 키는 AES-256(Fernet)으로 암호화해 저장합니다.",
    body: "평문으로 보관하지 않습니다. 복호화 키는 코드가 아니라 환경 변수에서 읽고, 저장소에는 암호문만 남습니다.",
  },
  {
    idx: "03",
    title: "미지원 Pine 함수가 하나라도 있으면 전체를 거부합니다.",
    body: "부분 실행으로 그럴듯한 숫자를 만드는 대신, 해석하지 못한다고 먼저 말합니다. 어느 함수 때문인지도 함께 돌려줍니다.",
  },
  {
    idx: "04",
    title: "리포트는 체결 가정과 데이터 출처를 결과 옆에 인쇄합니다.",
    body: "체결 시점, 수수료율, 슬리피지, 데이터 구간, 펀딩 반영 여부를 수익률과 같은 화면에 둡니다. 가정을 모르면 수익률도 읽을 수 없기 때문입니다.",
  },
];

export function BrandPanel() {
  return (
    <section className="auth-brand rise d1" aria-labelledby="auth-h1">
      <h1 className="auth-h1" id="auth-h1">
        Pine Script 전략을 검증하고, 검증한 그대로 주문까지 잇습니다.
      </h1>
      <p className="auth-lede">
        QuantBridge 는 TradingView 에서 쓰던 Pine Script 를 파싱해 자체
        인터프리터로 백테스트하고, 같은 전략을 거래소 주문으로 연결하는 로컬
        워크스페이스입니다. 백테스트와 실제 주문이 서로 다른 코드 경로를 타지
        않도록 만들었습니다.
      </p>

      <header className="auth-facts-head section-head">
        <p className="eyebrow">
          <span className="num">01</span> 확인 가능한 사실
        </p>
        <h2 className="section-title">숫자 자랑 대신 정책을 적습니다.</h2>
        <p className="section-desc">
          사용자 수나 체결 속도처럼 이 화면에서 확인할 수 없는 수치는 싣지
          않습니다. 대신 코드와 문서로 확인할 수 있는 규칙 네 가지를 적습니다.
        </p>
      </header>

      <ul className="card facts">
        {FACTS.map((f) => (
          <li key={f.idx} className="fact">
            <span className="fact-idx" aria-hidden="true">
              {f.idx}
            </span>
            <span>
              <span className="fact-title">{f.title}</span>
              <span className="fact-body">{f.body}</span>
            </span>
          </li>
        ))}
      </ul>

      <p className="auth-note">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="11" x2="12" y2="16.5" />
          <circle cx="12" cy="7.8" r="0.6" fill="currentColor" />
        </svg>
        계정은 QuantBridge 가 직접 관리합니다. 이메일과 비밀번호, 또는 소셜
        계정으로 워크스페이스에 들어갑니다.
      </p>
    </section>
  );
}
