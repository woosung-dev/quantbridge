<!-- UI/UX 풀 개편 작업의 의사결정·토큰 스펙 SSOT (P0~P7 핸드오프용) -->

# UI/UX 개편 — Context Notes (의사결정 기록)

> 작업 계획 SSOT: `~/.claude/plans/synthetic-rolling-scott.md`. 본 파일은 결정과 근거를 누적 기록한다.

## 확정 디자인 방향 (P0, 2026-07-01)

design-shotgun 4종(Terminal Tape / Indigo Quant / Oscilloscope / Slate & Ember) 비교 → **A "Terminal Tape" 확정**.

- **시그니처 = "P&L Tape"** — bullish/bearish 마이크로바의 연속 레일. 적용처: ① KPI 메트릭 카드 하단 기여도 스파크바, ② trade-table return 셀 인라인 매그니튜드 바(기존 패턴 표준화·확장), ③ 얇은 섹션 디바이더(선택). **계산된 미적 리스크는 여기 한 곳에 집중**(frontend-design "대담함은 한 곳에").
- **단일 액센트 정체성 = 시그널 코퍼**(amber/copper). C의 틸은 접목하지 않음 — 다크는 동일 코퍼의 웜 니어블랙 파생.
- **폰트:** Plus Jakarta Sans(display) + Inter(body) + JetBrains Mono(숫자) 유지. Terminal Tape는 mono를 구조적으로 더 활용 — **섹션/컬럼 레이블 = mono uppercase + letter-spacing(터미널 레이블 스타일)**.
- 산출물 보드: `~/.gstack/projects/quant-bridge/designs/design-language-20260701/` (variant-A.png + approved.json).

## Terminal Tape 토큰 시스템 (구현 SSOT — WCAG AA 검증)

> 정규 어휘 = **테마 인지 시맨틱 토큰**. `:root`(light) + `.dark`(dark) 양쪽에 전체셋 정의. 커스텀-var 라이트 전용 클래스는 deprecated.

### LIGHT (`:root`)

| 토큰                          | 값                                                             | 비고                             |
| ----------------------------- | -------------------------------------------------------------- | -------------------------------- |
| `--bg`                        | `#FAFAF7`                                                      | 웜 페이퍼                        |
| `--bg-alt` / muted            | `#F0EFEA`                                                      | 웜 섹션                          |
| `--card`                      | `#FFFFFF`                                                      |                                  |
| `--text-primary` / foreground | `#1A1D23`                                                      | 웜 그래파이트, on bg ~15:1       |
| `--text-secondary`            | `#565A63`                                                      | on white ~7:1                    |
| `--text-muted`                | `#767B85`                                                      | on white ~4.6:1 (소형 레이블 AA) |
| `--primary` (코퍼)            | `#B45309`                                                      | white text 5.0:1 ✅              |
| `--primary-hover`             | `#92400E`                                                      |                                  |
| `--primary-light`             | `#FCF3E9`                                                      | 아이콘/active nav bg             |
| `--primary-100`               | `#F5E2CC`                                                      | border/badge bg                  |
| `--primary-foreground`        | `#FFFFFF`                                                      | (다크에선 ink로 flip)            |
| `--ring`                      | `#B45309`                                                      |                                  |
| `--success`                   | `#047857`                                                      | 텍스트 등급, on white 4.8:1      |
| `--success-subtle`            | `#E7F5EF`                                                      | positive badge bg                |
| `--bullish`                   | `#0F9D6B`                                                      | 차트/바 등급(마이크로바·상승)    |
| `--destructive`               | `#DC2626`                                                      | on white 4.5:1                   |
| `--destructive-subtle`        | `#FCEBEA`                                                      |                                  |
| `--bearish`                   | `#E0413E`                                                      | 차트/바 등급                     |
| `--warning`                   | `#A16207`                                                      | --warning-subtle `#FAF0D7`       |
| `--border`                    | `#E7E5DE`                                                      | 웜 slate-200                     |
| `--border-strong`             | `#D4D1C8`                                                      |                                  |
| `--card-shadow`               | `0 1px 2px rgba(26,29,35,.04), 0 4px 16px rgba(26,29,35,.04)`  |                                  |
| `--card-shadow-hover`         | `0 2px 6px rgba(26,29,35,.06), 0 12px 32px rgba(26,29,35,.07)` |                                  |
| `--btn-primary-shadow`        | `0 4px 14px rgba(180,83,9,.22)`                                |                                  |

### DARK (`.dark` — 웜 니어블랙)

| 토큰                          | 값                                                    | 비고                                                                                                    |
| ----------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `--bg`                        | `#0E0F11`                                             | 웜 니어블랙                                                                                             |
| `--bg-alt` / muted            | `#17181B`                                             |                                                                                                         |
| `--card`                      | `#16171A`                                             |                                                                                                         |
| `--card-elevated`             | `#1C1D21`                                             |                                                                                                         |
| `--text-primary` / foreground | `#ECEAE3`                                             | 웜 오프화이트, ~15:1                                                                                    |
| `--text-secondary`            | `#A8A39A`                                             | ~7:1                                                                                                    |
| `--text-muted`                | `#8B867C`                                             | ~5:1                                                                                                    |
| `--primary` (코퍼, 밝게)      | `#E0832B`                                             | **`--primary-foreground` = `#1A1209`(ink)**: 다크 코퍼 버튼은 다크 텍스트 6.2:1 ✅ (white는 2.8:1 불가) |
| `--primary-hover`             | `#C9701E`                                             |                                                                                                         |
| `--primary-light`             | `rgba(224,131,43,.12)`                                |                                                                                                         |
| `--primary-100`               | `rgba(224,131,43,.22)`                                |                                                                                                         |
| `--ring`                      | `#E0832B`                                             | focus glow `0 0 0 3px rgba(224,131,43,.25)`                                                             |
| `--success`                   | `#34D399`                                             |                                                                                                         |
| `--success-subtle`            | `rgba(52,211,153,.14)`                                |                                                                                                         |
| `--bullish`                   | `#2DD4A7`                                             |                                                                                                         |
| `--destructive`               | `#F87171`                                             |                                                                                                         |
| `--destructive-subtle`        | `rgba(248,113,113,.14)`                               |                                                                                                         |
| `--bearish`                   | `#F6685E`                                             |                                                                                                         |
| `--warning`                   | `#E0A53C`                                             | --warning-subtle `rgba(224,165,60,.14)`                                                                 |
| `--border`                    | `rgba(236,234,227,.10)`                               | 웜틴트                                                                                                  |
| `--border-strong`             | `rgba(236,234,227,.16)`                               |                                                                                                         |
| `--card-shadow`               | `0 1px 2px rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.3)` |                                                                                                         |

### 핵심 구현 함정 (Plan 검증 발견)

1. **`@theme`(non-inline)는 빌드 타임 값 동결** → 테마 인지 커스텀 토큰은 `@theme inline`으로 이동. breakpoint/font/radius만 `@theme` 잔류.
2. `[data-theme="dash"]`(globals.css:182-213) **삭제**(테스트가 null 단언, 안전). `.dark`를 정규 다크로 승격하며 위 전체셋 재정의.
3. 잠복 버그 동시 수정: optimizer 차트 `hsl(var(--primary))`(유효하지 않은 CSS)→`var(--primary)`; trade-table 무효 `data-tone="positive/negative"`+하드코딩 `green-500/red-500`(10파일)→`text-bullish/bearish`; trading-chart OS-preference→앱 테마 연동.
4. `qb-*` keyframe ~30개 하드코딩 rgba → `color-mix(in srgb, currentColor …)`.
5. 라이브러리: lightweight-charts는 resolved hex prop(+문자열 `themeKey` dep, H-1), recharts/inline-SVG는 `var()` flip, Monaco `pine-light` 등록, Clerk `appearance.baseTheme` via ClerkThemeBridge(내부 client).

## 2026-07-05 — 백테스트 리포트 TV Strategy Tester IA 재편 (TV-parity sprint)

- **IA**: 완료 상태 = `report/backtest-report-shell` — [상시] KeyStatsStrip(총 PnL abs+%/최대 손실폭 abs+%/수익성 거래/수익지수) + AssumptionsCard + PerformanceChart(equity·B&H·Compare / drawdown / 거래별 PnL 히스토그램 + 접기) + [섹션 탭] 상세 결과(서브탭 오버뷰·수익률·벤치마킹·위험조정)/거래 분석(분포 histogram+donut)/런업&드로다운/거래 목록(2행 원장)/스트레스 테스트. detail page max-w 1080→1280.
- **차트 색 SSOT**: `lib/chart-tokens.ts` (`resolveChartTokens`/`useChartTheme` — useSyncExternalStore, setState-in-effect lint 금지). globals.css `--chart-equity/benchmark/compare/dd-*` 신설(기존 hex 값 그대로).
- **Surface Trust 3단계 null 정책**: 개별 지표 "—"(metric-table `nullPolicy`) / abs 병기·컬럼 숨김 / 섹션 잠금 empty state(재실행 유도). 인트라바 값 전부 "(bar 근사)" 라벨. FE 파생 waterfall 은 비용 전(gross) 항등식(`computeProfitStructure`) — BE net-기준 gross 필드와 혼용 금지.
- **제거**: metrics-cards → KeyStatsStrip / metrics-detail → DetailedResultsSection / trade-table → TradeLedgerTable. buildMddCaption 은 `_components/mdd-caption.ts` 로 이관.
