# 사이징 정규화 리런 (PR-2/B) — Context Notes

## 결정

- `--normalized` = config-only(form-tier `percent_of_equity=100`). `run_backtest_v2`/`BacktestConfig`
  변경 없음 → **엔진 diff 0** (PR-2 제약 충족). 사전확정: `BacktestConfig.default_qty_type/value`
  (types.py:40-41) + v2_adapter.py:100-101 form-tier 전달.
- before(비정규화) = 커밋된 `../2026-07-12-pine-batch-1h4h/results.json` (동일 엔진 — PR-1 무변경). 재-run 불필요.
- after(정규화) = 본 디렉토리 `results.json` (28 runnable 셀).

## 핵심 실측

- **Pine > form 실증**: DrFX(`percent_of_equity 100`)·RsiD(`fixed 2`)는 before=after 완전 동일 → Pine 선언 우선 확인.
- 정규화는 부호/트레이드 수 불변, 스케일만 압축. → 상대 순위 보존, 공정 비교 성립.
- **데모 후보 없음**: 두 국면 동시 플러스 전략 0. DrFX 만 최근 국면 플러스(+25.9%)지만 2024 마이너스.

## [가정] / [확인 필요]

- [확인 필요] RsiD·DrFX 는 Pine 사이징이라 form 정규화 불가 — 완전 동일 basis 비교하려면 스크립트 소스 편집 필요(범위 밖). RsiD(fixed 2 ≈8x)는 비교 코호트에서 제외.
- [가정] Ret < −100% 는 청산 모델 부재로 인한 명목 손실(엔진은 equity 음수 허용). 실계좌라면 청산.

## 선택 스텝(WFO/stress) — 스킵 결정

- 데모 후보가 명확히 0(No-Go)이라 WFO/stress 는 결론을 바꾸지 않음 + Celery/로컬 스택 기동 비용. **스킵**하고 근거만 기록.
  향후 특정 전략을 데모 승격 검토 시 그때 WFO(true OOS, C13 패턴)로 과최적 판정 권고.
