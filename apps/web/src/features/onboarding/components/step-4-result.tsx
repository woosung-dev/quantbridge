"use client";

// 온보딩 스텝 4: 백테스트 결과 요약 + CTA — C 디자인 언어 이식 (W3-E).
// 총수익 / 승률 / 트레이드 수 3 지표(ob-stat)만 간결히 표시 — 상세는 /backtests/:id 로.
// isError 분기(S1b ②)는 보존한다: 결과 조회 실패 시 완주 축하 헤드라인을 띄우지 않고
// (Surface Trust — 실데이터 없는 성공 표기 금지) 원인 A/B 를 구분해 안내한다.
// §4.9: metrics 스키마가 받치는 total_return / win_rate / num_trades 만 렌더한다. 벤치마크·
// 승패 분해 같은 미백업 파생값은 만들지 않는다(프로토타입은 캐논 샘플이라 인쇄했으나 라이브 X).

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CheckCircle2Icon,
  ChartNoAxesCombinedIcon,
  ExternalLinkIcon,
  RefreshCwIcon,
  TriangleAlertIcon,
} from "lucide-react";

import { useBacktest } from "@/features/backtest/hooks";
import { StateBox } from "@/components/state-box";
import { StatValue } from "@/components/stat-value";
import { EMPTY_CELL } from "@/lib/labels";
import { InfoIcon } from "@/components/info-icon";

// win_rate 는 0~1 분수(decimalString). 퍼센트로 표기한다.
function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return EMPTY_CELL;
  return `${(value * 100).toFixed(2)}%`;
}

// 수익률은 부호를 붙인다(프로토타입 캐논 "+127.40%"). 손실은 toFixed 가 이미 - 를 준다.
function formatSignedPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return EMPTY_CELL;
  const pct = (value * 100).toFixed(2);
  return `${value >= 0 ? "+" : ""}${pct}%`;
}

function toNumOrNull(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function Step4Result({
  backtestId,
  onFinish,
}: {
  backtestId: string | null;
  onFinish: () => void;
}) {
  const router = useRouter();
  const detail = useBacktest(backtestId ?? undefined);
  const metrics = detail.data?.metrics ?? null;

  const totalReturn = toNumOrNull(metrics?.total_return);
  const winRate = toNumOrNull(metrics?.win_rate);
  const numTrades = toNumOrNull(metrics?.num_trades);
  const isPending = detail.isLoading;

  // ── 결과 조회 실패 (isError 분기 보존) ─────────────────────────────────────
  if (backtestId && detail.isError) {
    const shortId = backtestId.slice(0, 8);
    return (
      <div>
        <div className="ob-lede">
          <span className="ob-lede-icon warn" aria-hidden="true">
            <TriangleAlertIcon strokeWidth={1.8} />
          </span>
          <div>
            <h2 className="ob-heading">결과를 불러오지 못했습니다</h2>
            <p className="ob-subtle break-keep">
              원인은 두 가지로 갈립니다. 어느 쪽인지에 따라 눌러야 할 버튼이 다릅니다.
            </p>
          </div>
        </div>

        <StateBox
          tone="failed"
          testId="onboarding-result-error"
          icon={<TriangleAlertIcon aria-hidden="true" />}
          title="결과를 불러오지 못했습니다."
          code={`GET /api/v1/backtests/${shortId}`}
        >
          <div className="ob-causes">
            <p className="ob-cause">
              <span className="ob-cause-tag">원인 A</span>
              <span>
                결과 조회 실패. 실행 ID 는 남아 있는데 서버가 결과를 돌려주지 않았습니다. 다시
                시도로 같은 ID 를 한 번 더 조회합니다.
              </span>
            </p>
            <p className="ob-cause">
              <span className="ob-cause-tag">원인 B</span>
              <span>
                세션 초기화. 온보딩 시작 시각에서 5분이 지나면 진행도가 첫 스텝으로 되돌아가면서
                실행 ID 를 잃습니다. 중간에 조작해도 이 5분은 연장되지 않습니다. 이때는 백테스트를
                다시 실행해야 합니다.
              </span>
            </p>
          </div>
          <div className="ob-actions center">
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => {
                void detail.refetch();
              }}
            >
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                onFinish();
                router.push("/dashboard");
              }}
              aria-label="대시보드로 이동"
            >
              대시보드로 이동
            </button>
          </div>
        </StateBox>
      </div>
    );
  }

  // ── 정상 결과 ──────────────────────────────────────────────────────────────
  const returnTone = totalReturn === null ? "" : totalReturn >= 0 ? " pos" : " neg";
  const winMeterWidth = winRate === null ? 0 : Math.max(0, Math.min(100, winRate * 100));

  return (
    <div>
      <div className="ob-lede">
        <span className="ob-lede-icon" aria-hidden="true">
          <CheckCircle2Icon strokeWidth={1.8} />
        </span>
        <div>
          <h2 className="ob-heading">첫 백테스트 완주</h2>
          <p className="ob-subtle break-keep">
            결과 요약을 확인하고 대시보드에서 본 작업을 시작하세요.
          </p>
        </div>
      </div>

      <div className="ob-stats">
        <div className="ob-stat">
          <p className="kpi-label">총 수익률</p>
          <p className={"kpi-value mono" + returnTone}>
            <StatValue isPending={isPending}>
              {totalReturn === null ? (
                <span
                  className="dim"
                  title="완료된 결과가 아직 없어 총 수익률을 계산할 수 없습니다."
                >
                  {EMPTY_CELL}
                </span>
              ) : (
                formatSignedPercent(totalReturn)
              )}
            </StatValue>
          </p>
          <div className="meter-void" aria-hidden="true" />
          <p className="kpi-foot">초기 자본 대비 누적 수익률입니다.</p>
        </div>

        <div className="ob-stat">
          <p className="kpi-label">승률</p>
          <p className="kpi-value mono">
            <StatValue isPending={isPending}>
              {winRate === null ? (
                <span className="dim" title="완료된 거래가 없어 승률의 분모가 없습니다.">
                  {EMPTY_CELL}
                </span>
              ) : (
                formatPercent(winRate)
              )}
            </StatValue>
          </p>
          {winRate === null ? (
            <div className="meter-void" aria-hidden="true" />
          ) : (
            <div className="meter">
              <span style={{ width: `${winMeterWidth}%` }} />
            </div>
          )}
          <p className="kpi-foot">완료 거래 기준 승리 비율입니다.</p>
        </div>

        <div className="ob-stat">
          <p className="kpi-label">거래 수</p>
          <p className="kpi-value mono">
            <StatValue isPending={isPending}>
              {numTrades === null ? (
                <span
                  className="dim"
                  title="이 실행에서는 진입 조건이 한 번도 성립하지 않았습니다."
                >
                  {EMPTY_CELL}
                </span>
              ) : (
                numTrades
              )}
            </StatValue>
          </p>
          <div className="meter-void" aria-hidden="true" />
          <p className="kpi-foot">진입·청산이 완료된 건수입니다.</p>
        </div>
      </div>

      {backtestId && (
        <Link href={`/backtests/${backtestId}`} className="ob-link ob-report-link">
          <ChartNoAxesCombinedIcon aria-hidden="true" />
          상세 리포트 보기
          <ExternalLinkIcon aria-hidden="true" />
        </Link>
      )}

      {/* ===== 다음 단계 (프로토타입 04) — 한 번의 백테스트는 가설 하나. ===== */}
      <div className="ob-next">
        <p className="ob-next-title">다음 단계</p>
        <p className="ob-subtle break-keep">
          한 번의 백테스트는 가설 하나입니다. 아래 순서로 검증 강도를 올리는 것을 권합니다.
        </p>
        <div className="cta-row">
          <article className="card cta recommended">
            <span className="cta-badge">권장</span>
            <span className="cta-icon" aria-hidden="true">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
              </svg>
            </span>
            <h3 className="cta-title">파라미터 최적화</h3>
            <p className="cta-desc">
              이동평균 길이 두 개를 그리드로 훑어 이 결과가 특정 값에만 기대고 있는지 확인합니다.
            </p>
            <p className="cta-meta">그리드 9조합 (3 x 3) · 바 단위 이벤트 루프</p>
            <Link className="btn btn-primary btn-block" href="/optimizer">
              최적화 실행
            </Link>
          </article>

          <article className="card cta">
            <span className="cta-icon" aria-hidden="true">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 17l4-6 4 3 4-8 6 11" />
                <line x1="3" y1="21" x2="21" y2="21" />
              </svg>
            </span>
            <h3 className="cta-title">스트레스 테스트</h3>
            <p className="cta-desc">
              거래 순서를 뒤섞었을 때 낙폭이 어디까지 벌어지는지 몬테카를로와 워크포워드로 봅니다.
            </p>
            <p className="cta-meta">이 백테스트의 거래를 그대로 입력으로 사용</p>
            <Link
              className="btn btn-block"
              href={backtestId ? `/backtests/${backtestId}` : "/backtests"}
            >
              스트레스 테스트 열기
            </Link>
          </article>

          <article className="card cta">
            <span className="cta-icon" aria-hidden="true">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <line x1="3" y1="10" x2="21" y2="10" />
                <line x1="7" y1="14.5" x2="11" y2="14.5" />
              </svg>
            </span>
            <h3 className="cta-title">데모 세션 연결</h3>
            <p className="cta-desc">
              Bybit 데모 한정. 가상 자금만 사용하며 실제 자금 손실은 없습니다. 같은 전략의 체결
              품질을 먼저 봅니다.
            </p>
            <p className="cta-meta">거래소 API 키 등록 필요</p>
            <Link className="btn btn-block" href="/trading">
              데모 연결 설정 열기
            </Link>
          </article>
        </div>
      </div>

      <p className="disclaimer ob-disclaimer">
        <InfoIcon />
        <span>
          백테스트 결과는 과거 데이터를 그대로 재생한 것이며, 미래 수익을 보장하지 않습니다.
        </span>
      </p>

      {/* 코퍼 주 액션은 위 '최적화 실행' 하나. 완주 종료는 중립 버튼으로 둔다(섹션당 코퍼 1개). */}
      <div className="ob-actions end">
        <button
          className="btn"
          type="button"
          onClick={() => {
            onFinish();
            router.push("/dashboard");
          }}
          aria-label="대시보드로 이동"
        >
          대시보드로 이동
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
