# QuantBridge — Stage 2 프로토타입

> **상태:** 확정 (2026-04-14)
> **디자인 시스템:** [DESIGN.md](../../DESIGN.md)
> **App Shell 패턴:** [DESIGN.md §10](../../DESIGN.md#10-app-shell-패턴-인증된-앱-페이지-공통)
> **방법론:** [development-methodology.md](../guides/development-methodology.md) (Stage 2)

---

## 프로토타입 목록

### 🎨 마케팅 (외부 방문자)
| # | 파일 | 화면 | URL (구현 시) | 테마 |
|:-:|------|------|-------------|------|
| 00 | [00-landing.html](./00-landing.html) | 랜딩 페이지 | `/` | Light + 플로팅 다크 쇼케이스 |

### 🔐 인증 (비로그인/온보딩)
| # | 파일 | 화면 | URL | 테마 |
|:-:|------|------|-----|------|
| 04 | [04-login.html](./04-login.html) | 로그인 / 회원가입 | `/sign-in`, `/sign-up` | Split-screen (다크 브랜드 + 라이트 폼) |
| 05 | [05-onboarding.html](./05-onboarding.html) | 온보딩 (4단계) | `/onboarding` | Light (standalone, no App Shell) |
| 11 | [11-error-pages.html](./11-error-pages.html) | 에러 페이지 (404 / 500 / 503) | `/404`, `/500`, `/503` | Light (standalone) |

### 🧠 전략 (Strategies)
| # | 파일 | 화면 | URL | 테마 |
|:-:|------|------|-----|------|
| 06 | [06-strategies-list.html](./06-strategies-list.html) | 전략 목록 | `/strategies` | Light + App Shell |
| 07 | [07-strategy-create.html](./07-strategy-create.html) | 전략 생성 (3-step 위저드) | `/strategies/new` | Light + App Shell |
| 01 | [01-strategy-editor.html](./01-strategy-editor.html) | 전략 편집 (Monaco) | `/strategies/[id]/edit` | Light + 다크 에디터 |

### 📊 백테스트 (Backtests)
| # | 파일 | 화면 | URL | 테마 |
|:-:|------|------|-----|------|
| 08 | [08-backtest-setup.html](./08-backtest-setup.html) | 백테스트 설정 | `/backtests/new` | Light + App Shell |
| 09 | [09-backtests-list.html](./09-backtests-list.html) | 백테스트 목록 | `/backtests` | Light + App Shell |
| 02 | [02-backtest-report.html](./02-backtest-report.html) | 백테스트 결과 리포트 | `/backtests/[id]` | Light + 다크 차트 |
| 10 | [10-trades-detail.html](./10-trades-detail.html) | 거래 내역 상세 | `/backtests/[id]/trades` | Light + App Shell |

### ⚡ 트레이딩 (Trading)
| # | 파일 | 화면 | URL | 테마 |
|:-:|------|------|-----|------|
| 03 | [03-trading-dashboard.html](./03-trading-dashboard.html) | 트레이딩 대시보드 | `/dashboard` | **Full Dark** + App Shell |

---

## 완성도 현황

**총 12개 파일 / 35개 페이지 계획**

| 구분 | 완료 | 남은 페이지 |
|------|:---:|----------|
| 랜딩/인증/에러 | 4개 | — |
| Phase 1 MVP | **7개** ✅ | — |
| Phase 2 (고급 백테스트) | 0개 | 8개 (멀티심볼, Monte Carlo, Walk-Forward, 최적화, 템플릿 등) |
| Phase 3 (데모 트레이딩) | 0개 | 7개 (거래소 연동, 세션, 라이브 모니터링 등) |
| Phase 4 (라이브) | 0개 | 5개 (라이브 전환, 리스크 관리, 알림, 리포트) |
| 공통 설정 | 0개 | 4개 (프로필, 빌링, 알림센터, 도움말) |

**Tier 1 (Phase 1 MVP) 완료** — MVP 개발에 필요한 모든 화면 확보.

---

## 보는 방법

```bash
cd docs/prototypes
python3 -m http.server 8899 --bind 127.0.0.1

# 브라우저에서 http://localhost:8899/ 열기
```

각 파일을 브라우저로 직접 드래그해도 작동합니다 (Google Fonts 외부 로딩만 필요).

---

## App Shell 통일 원칙

모든 인증된 앱 페이지 (01, 02, 03, 06, 07, 08, 09, 10)는 **동일한 App Shell** 구조를 공유:

### Sidebar (220px 고정 / 60px 축소 / 햄버거 모바일)
```
로고
─────────
대시보드
전략
템플릿
백테스트
트레이딩
거래소
─────────
알림 (3)
설정
김지훈 프로필 (프로)
```

### Global Header (60px)
```
[브레드크럼] ... [⌘K 검색] ... [페이지별 CTA] [알림] [아바타]
```

**테마만 다르고 구조는 동일:**
- 01, 02, 06, 07, 08, 09, 10 → Light 테마
- 03 (대시보드) → Dark 테마 (트레이딩 UI 표준)

**테마별 토큰:** DESIGN.md §10.4 "테마별 App Shell 색상" 참조

---

## 프로토타입 역할

1. **개발 스펙** — Frontend 구현 시 레퍼런스 (Next.js + shadcn/ui + Tailwind v4로 재구성)
2. **UX 검증** — 구현 전 레이아웃/동선 문제 발견
3. **이해관계자 합의** — 비주얼 톤/방향성 확인

### 실제 구현 매핑

| 프로토타입 요소 | 실제 구현 |
|---------------|----------|
| Monaco 풍 에디터 | `@monaco-editor/react` |
| 캔들스틱/자산 곡선 차트 | TradingView Lightweight Charts v4 |
| 히트맵/히스토그램 | Recharts 또는 Plotly |
| 사이드바/카드/버튼 | shadcn/ui v4 컴포넌트 |
| 테마 토큰 | `tailwind.config.ts` + CSS 변수 (DESIGN.md §14) |
| 아이콘 | Lucide Icons (`lucide-react`) |
| 폼 검증 | react-hook-form + Zod v4 |
| 실시간 업데이트 | Socket.IO client + React Query |
| 날짜 피커 | shadcn/ui DatePicker |
| 테이블 | TanStack Table v8 |

### 주의 사항

- 정적 HTML이므로 **실제 인터랙션은 불가** (링크, 폼 제출 등)
- Pine Script 코드는 시각 데모용 (실행 불가)
- 차트는 모두 SVG로 수작업 — 실제는 차트 라이브러리 사용
- Mock 데이터는 예시용 (샤프 2.47, 승률 68.4% 등)
- 애니메이션은 CSS only (실제 구현 시 Framer Motion 등 고려)

---

## Tier 진행 계획

- **Tier 1 (Phase 1 MVP)** — ✅ 완료 (11개 페이지, 이 중 8개는 App Shell 공유)
- **Tier 2 (Phase 2~4)** — 필요 시 추가 (PRD 확정 후 진행 권장)
- **Tier 3 (공통 설정)** — 필요 시 추가 (프로필, 빌링, 알림센터, 도움말)

**Stage 3 (스프린트 계획) 진입 가능 상태.**
