// 10 다음 단계 — variant-c "이 결과로 무엇을 할까요?" 이식. 공용 .cta-row/.cta 를 소비한다.
// 프로토타입 variant-c.html:1621-1652 의 3 CTA(최적화 권장 / 스트레스 / 데모 연결) 구조.
// meta 문구는 §4.5(그리드 최대 9조합) · §4.9(ETA·남은 시간 인쇄 금지)에 맞춰 교정한다.
// (프로토타입의 "81조합 · 예상 4분" · "예상 2분" 은 캐논 위반이라 그대로 옮기지 않는다.)

import Link from "next/link";
import { Activity, PlugZap, SlidersHorizontal } from "lucide-react";

interface ReportNextStepsProps {
  /** 스트레스 테스트 섹션 앵커 대상 id. */
  stressTestAnchorId: string;
}

export function ReportNextSteps({ stressTestAnchorId }: ReportNextStepsProps) {
  return (
    <div className="cta-row" data-testid="report-next-steps">
      <article className="card cta recommended">
        <span className="cta-badge">권장</span>
        <span className="cta-icon" aria-hidden="true">
          <SlidersHorizontal />
        </span>
        <h3 className="cta-title">파라미터 최적화</h3>
        <p className="cta-desc">
          파라미터를 격자로 훑어 이 결과가 특정 값에만 기대고 있는지 확인합니다.
        </p>
        <p className="cta-meta">그리드 최대 9조합</p>
        <Link className="btn btn-primary btn-block" href="/optimizer">
          최적화 실행
        </Link>
      </article>

      <article className="card cta">
        <span className="cta-icon" aria-hidden="true">
          <Activity />
        </span>
        <h3 className="cta-title">스트레스 테스트</h3>
        <p className="cta-desc">
          몬테카를로와 워크포워드로 거래 순서가 바뀌었을 때의 낙폭 분포를 봅니다.
        </p>
        <p className="cta-meta">몬테카를로 1,000회 표본</p>
        <a className="btn btn-block" href={`#${stressTestAnchorId}`}>
          스트레스 테스트 열기
        </a>
      </article>

      <article className="card cta">
        <span className="cta-icon" aria-hidden="true">
          <PlugZap />
        </span>
        <h3 className="cta-title">데모 계정에 연결</h3>
        <p className="cta-desc">
          실자금 없이 거래소 데모 키로 같은 전략을 돌려 체결 품질을 확인합니다.
        </p>
        <p className="cta-meta">거래소 API 키 등록 필요</p>
        <Link className="btn btn-block" href="/trading">
          거래소 연결로 이동
        </Link>
      </article>
    </div>
  );
}
