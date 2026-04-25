// Sprint 11 Phase B — Privacy Policy (개인정보 처리방침). 법무 임시.

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy · QuantBridge",
  description: "QuantBridge Beta 개인정보 처리방침 (법무 임시본)",
};

export default function PrivacyPage() {
  return (
    <main
      id="main-content"
      className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[760px] flex-col gap-6 px-6 py-14"
    >
      <div className="rounded-md border-l-4 border-amber-500 bg-amber-50 p-4 text-sm text-amber-900">
        <strong>[법무 임시 — 법적 효력 제한적]</strong> 본 방침은 H2 Beta 단계 임시 템플릿입니다.
        H2 말 (~2026-06-30) 한국 변호사 검토본으로 교체 예정. 개인정보보호법상 필수 고지 항목은
        정식본에서 보완.
      </div>

      <h1 className="font-display text-3xl font-extrabold tracking-tight">
        Privacy Policy / 개인정보 처리방침
      </h1>

      <section className="space-y-3 text-sm leading-relaxed text-[color:var(--text-secondary)]">
        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">1. Data We Collect / 수집 정보</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <strong>계정 정보:</strong> Clerk 을 통한 이메일, 사용자명, 가입 시점, 국가 코드
            (ISO 3166-1 alpha-2)
          </li>
          <li>
            <strong>거래소 연동:</strong> API Key / Secret (AES-256 암호화 저장), 거래소명,
            모드 (demo/live)
          </li>
          <li>
            <strong>전략 데이터:</strong> 업로드한 Pine Script 코드, 메타데이터, 백테스트
            파라미터 / 결과
          </li>
          <li>
            <strong>기술 로그:</strong> 요청 IP (rate-limit 용 해시 형태), User-Agent, 에러
            traceback, 거래 시도 이력
          </li>
        </ul>

        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">2. How We Use Data / 이용 목적</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>서비스 제공 (백테스트 실행, 거래 집행, 대시보드 표시)</li>
          <li>Kill Switch 및 안전 장치 작동</li>
          <li>보안 감사 및 악용 탐지</li>
          <li>지원 요청 응대</li>
          <li>서비스 개선을 위한 집계 분석 (개인 식별 불가 형태)</li>
        </ul>

        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">3. Third-Party Processors / 제3자 처리</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>
            <strong>Clerk</strong> — 인증 (이메일, 사용자명, MFA)
          </li>
          <li>
            <strong>Bybit / OKX</strong> — 주문 실행, OHLCV 수집 (사용자가 연동한 계정 한정)
          </li>
          <li>
            <strong>Cloudflare</strong> — CDN, WAF, DDoS 보호
          </li>
          <li>
            <strong>Grafana Cloud</strong> — 지표·로그 수집 (집계형)
          </li>
          <li>
            <strong>Resend</strong> — 이메일 발송 (Waitlist, 알림)
          </li>
        </ul>

        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">4. Data Retention / 보관 기간</h2>
        <p>
          계정 활성 기간 + 계정 삭제 후 30일. 단 법정 보존 의무 (전자금융거래법 5년 등) 대상
          데이터는 해당 기간 보존.
        </p>

        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">5. Your Rights / 사용자 권리</h2>
        <p>
          개인정보보호법에 따라 열람, 정정, 삭제, 처리정지를 요청할 수 있습니다. 요청은{" "}
          <a
            href="mailto:privacy@quantbridge.ai"
            className="underline hover:text-[color:var(--text-primary)]"
          >
            privacy@quantbridge.ai
          </a>{" "}
          로 연락하거나 계정 설정에서 직접 수행.
        </p>

        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">6. Security / 보안 조치</h2>
        <p>
          거래소 API Key 는 AES-256 (Fernet MultiFernet) 으로 암호화 저장. Database 는
          encryption-at-rest. Redis/Postgres 는 VPC 내부 격리. 모든 외부 통신은 TLS 1.2+.
        </p>

        <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">7. Contact / 문의</h2>
        <p>
          <strong>개인정보보호책임자:</strong> 본인 (H2 Beta 단계, H3 에 별도 담당자 지정 예정).{" "}
          <a
            href="mailto:privacy@quantbridge.ai"
            className="underline hover:text-[color:var(--text-primary)]"
          >
            privacy@quantbridge.ai
          </a>
        </p>
      </section>

      <p className="pt-4 text-xs text-[color:var(--text-tertiary)]">
        최종 개정: 2026-04-25 (Beta 임시본). 정식 개정본은 H2 말 공지.
      </p>
    </main>
  );
}
