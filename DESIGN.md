# QuantBridge — 디자인 시스템

> **상태:** 확정 (Stage 2 산출물)
> **일자:** 2026-04-14
> **레퍼런스:** `/tmp/quantbridge-final.html` (디자인 프로토타입)
> **도구:** ui-ux-pro-max (스타일: Swiss Minimalism + Glassmorphism 하이브리드)

---

## 1. 디자인 원칙

| 원칙 | 설명 |
|------|------|
| **명료성 우선** | 금융 데이터는 장식보다 가독성. 모든 숫자는 모노스페이스, 충분한 대비 |
| **라이트 바디 + 다크 대시보드** | 마케팅/설정 화면은 라이트, 트레이딩 대시보드는 다크 — 맥락에 맞는 테마 전환 |
| **일관된 토큰** | 색상·간격·타이포를 CSS 변수로 관리, 하드코딩 금지 |
| **접근성 기본** | WCAG AA 이상 (4.5:1 텍스트 대비), 키보드 네비게이션, reduced-motion 지원 |
| **이모지 금지** | 모든 아이콘은 SVG (Lucide 스타일). 이모지를 구조적 아이콘으로 사용 금지 |

---

## 2. 색상 토큰

### 2.1 Light Theme (마케팅, 설정, 일반 페이지)

```css
:root {
  /* 배경 */
  --bg:              #FAFBFC;     /* 메인 배경 */
  --bg-alt:          #F1F5F9;     /* 대체 섹션 배경 (slate-100) */
  --card:            #FFFFFF;     /* 카드/서피스 */

  /* 텍스트 */
  --text-primary:    #0F172A;     /* 제목, 본문 강조 (slate-900) */
  --text-secondary:  #475569;     /* 본문, 설명 (slate-600) */
  --text-muted:      #94A3B8;     /* 힌트, 비활성 (slate-400) */

  /* 브랜드 */
  --primary:         #2563EB;     /* 메인 액션 (blue-600) */
  --primary-hover:   #1D4ED8;     /* 호버 (blue-700) */
  --primary-light:   #EFF6FF;     /* 아이콘 배경 (blue-50) */
  --primary-100:     #DBEAFE;     /* 보더, 뱃지 배경 (blue-100) */

  /* 시맨틱 */
  --success:         #059669;     /* 긍정 액션 (emerald-600) */
  --success-light:   #D1FAE5;     /* 성공 배경 */
  --destructive:     #DC2626;     /* 위험, 삭제 (red-600) */
  --destructive-light: #FEE2E2;   /* 에러 배경 */

  /* 보더 & 구분 */
  --border:          #E2E8F0;     /* 기본 보더 (slate-200) */
  --border-dark:     #CBD5E1;     /* 강조 보더 (slate-300) */
}
```

### 2.2 Dark Theme (트레이딩 대시보드, 차트 화면)

```css
:root {
  /* 배경 */
  --dash-bg:                #0B1120;              /* 메인 배경 */
  --dash-surface:           rgba(255,255,255,0.04); /* 카드 */
  --dash-surface-elevated:  rgba(255,255,255,0.07); /* 강조 카드 */

  /* 텍스트 */
  --dash-text:       #EDEDEF;     /* 제목, 본문 */
  --dash-text-muted: #8A8F98;     /* 힌트, 레이블 */

  /* 액센트 */
  --dash-accent:       #6366F1;                   /* 인디고 (indigo-500) */
  --dash-accent-glow:  rgba(99,102,241,0.25);     /* 글로우 쉐도우 */

  /* 금융 데이터 */
  --dash-green:      #34D399;     /* 수익, Long 포지션 (emerald-400) */
  --dash-red:        #F87171;     /* 손실, Short 포지션 (red-400) */

  /* 보더 */
  --dash-border:     rgba(255,255,255,0.08);
}
```

### 2.3 차트 전용 색상

```css
/* 캔들스틱 */
--chart-bullish:    #26A69A;     /* 양봉 (TradingView 표준) */
--chart-bearish:    #EF5350;     /* 음봉 */

/* 영역 차트 그라데이션 */
--chart-area-top:   rgba(52, 211, 153, 0.30);  /* #34D399 30% */
--chart-area-bottom: rgba(52, 211, 153, 0.00); /* 투명 */
--chart-line:       #34D399;                    /* 라인 스트로크 */

/* 그리드 & 축 */
--chart-grid:       rgba(255,255,255,0.04);     /* 다크 모드 그리드 */
--chart-axis:       #8A8F98;                    /* 축 레이블 */
```

### 2.4 색상 사용 규칙

| 용도 | Light Theme | Dark Theme |
|------|------------|------------|
| 수익/이익 | `--success` #059669 | `--dash-green` #34D399 |
| 손실/위험 | `--destructive` #DC2626 | `--dash-red` #F87171 |
| Long 포지션 배지 | bg `--success-light`, text `--success` | bg `rgba(52,211,153,0.15)`, text `--dash-green` |
| Short 포지션 배지 | bg `--destructive-light`, text `--destructive` | bg `rgba(248,113,113,0.15)`, text `--dash-red` |
| CTA 버튼 | bg `--primary`, text `#FFFFFF` | bg `--dash-accent`, text `#FFFFFF` |
| 비활성 탭 | text `--text-muted` | text `--dash-text-muted` |
| 활성 탭 | text `--primary`, border `--primary` | text `--dash-text`, border `--dash-accent` |

---

## 3. 타이포그래피

### 3.1 폰트 패밀리

| 용도 | 폰트 | Weight | 적용 |
|------|------|--------|------|
| 제목 (h1~h4) | Plus Jakarta Sans | 600, 700, 800 | 히어로 헤드라인, 섹션 타이틀, 카드 제목 |
| 본문 | Inter | 400, 500, 600 | 설명, 레이블, 네비게이션 |
| 데이터/숫자 | JetBrains Mono | 500, 700 | 가격, 수익률, 통계, 코드, 시간 |

```css
/* Google Fonts 임포트 */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap');

/* CSS 적용 */
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
h1, h2, h3, h4, h5 { font-family: 'Plus Jakarta Sans', sans-serif; }
.mono, [data-type="number"] { font-family: 'JetBrains Mono', monospace; }
```

### 3.2 타입 스케일

| 레벨 | 사이즈 | Weight | Line Height | 용도 |
|------|--------|--------|-------------|------|
| Display | `clamp(2.5rem, 5vw, 3.75rem)` | 800 | 1.15 | 히어로 헤드라인 |
| H2 | `clamp(1.75rem, 3vw, 2.25rem)` | 700 | 1.2 | 섹션 타이틀 |
| H3 | `1.05~1.15rem` | 600 | 1.3 | 카드 제목, 서브 타이틀 |
| Body | `1rem (16px)` | 400 | 1.6 | 본문 |
| Body Small | `0.875rem` | 400 | 1.6 | 카드 설명, 피처 리스트 |
| Caption | `0.8rem` | 500 | 1.5 | 레이블, 배지 |
| Mono Data | `0.85~2rem` | 700 | 1.2 | 숫자, 가격, 통계 |

### 3.3 타이포 규칙

- 제목 letter-spacing: `-0.02em` (Display, H2)
- 본문 letter-spacing: `0` (기본)
- 금융 숫자는 **반드시** JetBrains Mono — 탭룰러 피겨로 열 정렬 유지
- 코드 스니펫 (Pine Script 등): JetBrains Mono, `0.75rem`, line-height `1.7`
- 최소 본문 크기: `16px` (모바일 iOS 자동 줌 방지)
- 줄 길이: 모바일 35~60자, 데스크톱 60~75자 (`max-width: 520px` 설명 텍스트)

---

## 4. 간격 & 레이아웃

### 4.1 Spacing Scale (8px 베이스)

```
4px  — 아이콘 내부 간격
8px  — 밀접 요소 gap
12px — 소형 gap (배지, 필)
16px — 기본 gap (카드 내부 요소)
20px — 카드 그리드 gap
24px — 컨테이너 좌우 패딩, 카드 패딩 기본
28px — 카드 패딩 (데스크톱)
32px — 섹션 내 블록 간격
48px — 섹션 헤더 → 콘텐츠
56px — 푸터 상단 패딩
72px — CTA 섹션 패딩
80px — 섹션 상하 패딩 (데스크톱)
```

### 4.2 Max Width & Container

```css
.container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

/* 대시보드 컨테이너 */
.dash-container { max-width: 1000px; }

/* FAQ, 좁은 콘텐츠 */
.narrow { max-width: 720px; }
```

### 4.3 반응형 브레이크포인트

| 브레이크포인트 | 그리드 변경 |
|-------------|-----------|
| `1440px` | max-width 컨테이너 |
| `1024px` | 기능 카드 3→2열, 벤토 3→2열 |
| `768px` | 전체 1열, 히어로 스택, 가격 1열, 스텝 2열, 네비 접힘, 대시보드 1열 |
| `375px` | 패딩 축소 (24→16px), CTA 풀와이드, 스텝 1열 |

### 4.4 Z-Index 스케일

```css
--z-base:    0;      /* 기본 콘텐츠 */
--z-card:    1;      /* 플로팅 카드 */
--z-sticky:  10;     /* sticky 요소 */
--z-overlay: 50;     /* 오버레이 배경 */
--z-modal:   60;     /* 모달 */
--z-nav:     100;    /* 네비게이션 */
```

---

## 5. Border Radius 토큰

```css
--radius-sm:  6px;   /* 인풋, 작은 배지 */
--radius-md:  10px;  /* 버튼, 필 */
--radius-lg:  14px;  /* 카드, FAQ 아이템 */
--radius-xl:  18px;  /* 대시보드 컨테이너, 브라우저 목업 */
--radius-full: 50%;  /* 아바타, 아이콘 원형 */
--radius-pill: 20px; /* 필/배지 (공지 배너, 거래소 태그) */
```

---

## 6. 그림자 (Elevation)

```css
/* Light Theme 카드 */
--card-shadow:       0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04);
--card-shadow-hover: 0 2px 8px rgba(0,0,0,0.08), 0 16px 40px rgba(0,0,0,0.06);

/* 네비게이션 (스크롤 시) */
--nav-shadow:        0 1px 3px rgba(0,0,0,0.06);

/* CTA 버튼 */
--btn-primary-shadow:       0 4px 14px rgba(37,99,235,0.25);
--btn-primary-shadow-hover: 0 6px 20px rgba(37,99,235,0.35);

/* Dark Theme — 글로우 */
--dash-glow:         0 0 80px rgba(99,102,241,0.06);  /* 배경 앰비언트 */
--dash-accent-glow:  0 0 20px rgba(99,102,241,0.25);  /* CTA 글로우 */

/* 브라우저 목업 */
--mockup-shadow:     0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04);
```

---

## 7. 컴포넌트 패턴

### 7.1 버튼

| 타입 | 배경 | 텍스트 | 보더 | 용도 |
|------|------|--------|------|------|
| Primary | `--primary` | `#FFFFFF` | 없음 | 메인 CTA, 폼 제출 |
| Secondary | `#FFFFFF` | `--text-secondary` | `1.5px --border` | 보조 액션 |
| Ghost | 투명 | `--text-secondary` | 없음 | 네비 링크, 텍스트 버튼 |
| Destructive | `--destructive` | `#FFFFFF` | 없음 | 삭제, 위험 액션 |
| Outline (Pricing) | `#FFFFFF` | `--text-secondary` | `1.5px --border` | 가격 카드 하단 |
| Filled (Pricing) | `--primary` | `#FFFFFF` | 없음 | 추천 가격 카드 |
| Dark CTA | `--dash-accent` | `#FFFFFF` | 없음 | 다크 테마 CTA |

**공통 속성:**
```css
min-height: 48px;           /* 터치 타겟 */
padding: 14px 32px;
border-radius: 10px;
font-weight: 600;
font-size: 0.95rem;
transition: all 200ms ease;
cursor: pointer;
display: inline-flex;
align-items: center;
gap: 8px;
```

### 7.2 카드

```css
/* 기본 카드 (Light) */
.card {
  background: var(--card);
  border-radius: var(--radius-lg);     /* 14px */
  padding: 28px;
  box-shadow: var(--card-shadow);
  transition: transform 200ms ease, box-shadow 200ms ease;
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--card-shadow-hover);
}

/* 글래스 카드 (Dark) */
.glass-card {
  background: var(--dash-surface);      /* rgba(255,255,255,0.04) */
  backdrop-filter: blur(20px);
  border: 1px solid var(--dash-border); /* rgba(255,255,255,0.08) */
  border-radius: var(--radius-lg);
}

/* 강조 글래스 카드 */
.glass-card-elevated {
  background: var(--dash-surface-elevated); /* rgba(255,255,255,0.07) */
}
```

### 7.3 인풋

```css
/* Light Theme */
input {
  background: #FFFFFF;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);     /* 6px */
  padding: 14px 18px;
  font-size: 0.9rem;
  min-height: 48px;                    /* 터치 타겟 */
  transition: border-color 200ms ease;
}
input:focus {
  border-color: var(--primary);
  outline: 2px solid rgba(37,99,235,0.15);
  outline-offset: 0;
}

/* Dark Theme */
.dash-input {
  background: var(--dash-surface);
  border: 1px solid var(--dash-border);
  color: var(--dash-text);
}
```

### 7.4 배지/필

```css
/* 공지 필 */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--primary-light);
  border: 1px solid var(--primary-100);
  color: var(--primary);
  font-size: 0.8rem;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: var(--radius-pill);   /* 20px */
}

/* 포지션 배지 */
.badge-long  { background: rgba(52,211,153,0.15); color: var(--dash-green); }
.badge-short { background: rgba(248,113,113,0.15); color: var(--dash-red); }
```

### 7.5 아이콘 시스템

- **라이브러리:** Lucide 스타일 inline SVG
- **크기:** 기본 `22×22`, 네비/소형 `16×16`, 피처 아이콘 `22×22` (44px 원형 컨테이너)
- **스트로크:** `1.5px`, `stroke-linecap: round`, `stroke-linejoin: round`
- **색상:** Light에서 `stroke: var(--primary)`, Dark에서 `stroke: var(--dash-text)` 또는 `var(--dash-accent)`

```css
.icon {
  width: 22px;
  height: 22px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* 피처 카드 아이콘 컨테이너 */
.icon-container {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## 8. 인터랙션 & 애니메이션

### 8.1 트랜지션

```css
/* 기본 — 모든 인터랙티브 요소 */
transition: all 200ms ease;

/* 카드 호버 */
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--card-shadow-hover);
}

/* 버튼 호버 */
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--btn-primary-shadow-hover);
}
```

### 8.2 키프레임 애니메이션

```css
/* 히어로 플로팅 카드 */
@keyframes heroFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
/* 6s ease-in-out infinite */

/* 실시간 모니터링 도트 펄스 */
@keyframes livePulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
/* 3s linear infinite, 도트 간 0.5s stagger */
```

### 8.3 Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 9. 접근성 기준

| 항목 | 기준 | 구현 |
|------|------|------|
| 텍스트 대비 | WCAG AA (4.5:1) | `#0F172A` on `#FAFBFC` = 17.5:1 ✅ |
| 보조 텍스트 대비 | WCAG AA (4.5:1) | `#475569` on `#FFFFFF` = 7.1:1 ✅ |
| 버튼 대비 | WCAG AA | `#FFFFFF` on `#2563EB` = 8.6:1 ✅ |
| 다크 텍스트 대비 | WCAG AA | `#EDEDEF` on `#0B1120` = 15.2:1 ✅ |
| 포커스 표시 | `:focus-visible` | `outline: 2px solid var(--primary); outline-offset: 2px;` |
| 터치 타겟 | 최소 44×44px | 버튼 `min-height: 48px`, 아이콘 버튼 `44px` |
| 폼 레이블 | 항상 존재 | 시각적 히든 가능하나 `<label>` 필수 |
| 색상만으로 정보 전달 금지 | 텍스트/아이콘 보조 | Long/Short 배지에 텍스트 포함, 수익/손실에 +/- 기호 포함 |
| 키보드 내비게이션 | Tab 순서 | 시각적 순서와 일치 |
| 스크린 리더 | aria-label | 아이콘 버튼에 `aria-label` 필수 |

---

## 10. App Shell 패턴 (인증된 앱 페이지 공통)

**원칙:** 인증된 모든 앱 페이지는 동일한 App Shell 구조를 사용한다. 테마(라이트/다크)만 바뀌고 **구조·위치·동작은 동일**.

### 10.1 레이아웃 구조

```
┌─ Global Header (height 60px, sticky, z-index: 100) ──────────┐
│ [로고] [브레드크럼] ... [검색] [알림] [프로필]                   │
├─ Sidebar (220px expanded / 60px collapsed) ┬─── 콘텐츠 ────┤
│                                           │               │
│  네비게이션 메뉴                             │  (페이지별    │
│                                           │   다름)       │
│                                           │               │
│  ─── divider ───                          │               │
│                                           │               │
│  설정 / 프로필 (하단 고정)                   │               │
└───────────────────────────────────────────┴───────────────┘
```

### 10.2 Sidebar 사양

| 속성 | 확장 모드 (기본) | 축소 모드 |
|------|---------------|----------|
| Width | `220px` | `60px` |
| 표시 | 아이콘 + 레이블 | 아이콘만, hover 시 툴팁 |
| 토글 위치 | 사이드바 상단/하단 chevron 버튼 | — |
| 기본 동작 | 데스크톱: 확장, 1200px↓: 축소, 768px↓: 숨김+햄버거 | — |

**네비게이션 항목 (순서 고정):**

```
순서  아이콘       레이블          경로
1     home        대시보드         /dashboard
2     code        전략            /strategies
3     layers      템플릿          /templates
4     bar-chart   백테스트         /backtests
5     zap         트레이딩         /trading
6     globe       거래소          /exchanges
───── divider ─────
7     bell        알림            /notifications  (뱃지 표시)
8     settings    설정            /settings       (하단)
9     user-avatar 프로필          /profile        (하단)
```

**활성 상태 스타일:**

```css
/* Light Theme */
.nav-item.active {
  background: var(--primary-light);  /* #EFF6FF */
  color: var(--primary);             /* #2563EB */
  border-left: 3px solid var(--primary);
}
.nav-item.active svg { stroke: var(--primary); }

/* Dark Theme */
.nav-item.active {
  background: rgba(99,102,241,0.12);
  color: var(--dash-accent);         /* #6366F1 */
  border-left: 3px solid var(--dash-accent);
}
.nav-item.active svg { stroke: var(--dash-accent); }
```

**Hover 상태:**
- Light: `background: var(--bg-alt);` (#F1F5F9)
- Dark: `background: rgba(255,255,255,0.04);`

### 10.3 Global Header 사양

**공통 요소 (좌→우):**

| 위치 | 요소 | 설명 |
|------|------|------|
| Left 1 | Sidebar 토글 버튼 | 44×44, 햄버거 아이콘 (모바일) 또는 chevron (데스크톱) |
| Left 2 | 브레드크럼 / 페이지 제목 | 페이지 컨텍스트 표시 |
| Center | 검색 바 (선택적) | `⌘K` 글로벌 검색, 데스크톱만 표시 |
| Right 1 | 페이지 컨텍스트 | 페이지별 고유 요소 (예: 실시간 잔고, DEMO/LIVE 토글) |
| Right 2 | 알림 벨 | 44×44, 새 알림 뱃지 |
| Right 3 | 프로필 아바타 | 36px 원형, 드롭다운 메뉴 |

**높이:** `60px` 고정, `sticky`, `border-bottom: 1px solid var(--border)` (라이트) / `var(--dash-border)` (다크)

### 10.4 테마별 App Shell 색상

**Light Theme:**
```css
--shell-bg: #FFFFFF;                 /* 헤더·사이드바 배경 */
--shell-border: var(--border);       /* #E2E8F0 */
--shell-text: var(--text-primary);   /* #0F172A */
--shell-text-muted: var(--text-muted); /* #94A3B8 */
--shell-hover: var(--bg-alt);        /* #F1F5F9 */
```

**Dark Theme:**
```css
--shell-bg: var(--dash-bg);          /* #0B1120 */
--shell-border: var(--dash-border);  /* rgba(255,255,255,0.08) */
--shell-text: var(--dash-text);      /* #EDEDEF */
--shell-text-muted: var(--dash-text-muted); /* #8A8F98 */
--shell-hover: rgba(255,255,255,0.04);
```

### 10.5 페이지별 차이 (허용 범위)

| 요소 | 공통 | 페이지별 차이 허용 |
|------|------|-----------------|
| Sidebar 구조/항목 | ✅ 동일 | ❌ |
| Sidebar 활성 항목 | ❌ | ✅ (페이지마다 다름) |
| Header 높이/위치 | ✅ 동일 | ❌ |
| Header 공통 요소 (알림, 프로필) | ✅ 동일 | ❌ |
| Header 컨텍스트 영역 | ❌ | ✅ (대시보드는 잔고, 편집은 저장 버튼 등) |
| 콘텐츠 영역 | ❌ | ✅ (완전 자유) |
| 테마 (라이트/다크) | ❌ | ✅ (페이지 성격에 따라) |

### 10.6 반응형 동작

```
≥1440px:  Sidebar 확장 (220px), 헤더 모든 요소 표시
1200px~:  Sidebar 확장, 검색 축소
1024px~:  Sidebar 축소 가능 (60px), 검색 숨김
768px~:   Sidebar 숨김 + 햄버거, 헤더 간소화
<768px:   모바일 최적화, Sidebar는 drawer
```

---

## 11. 페이지별 테마 적용

| 페이지 | 테마 | 비고 |
|--------|------|------|
| 랜딩 페이지 | Light + 다크 대시보드 섹션 | 프로토타입 완성 |
| 로그인/회원가입 | Light | Clerk UI 커스터마이징 |
| 대시보드 (트레이딩) | **Dark** | `--dash-*` 토큰 전체 적용 |
| 전략 편집 | Light (에디터는 Dark) | 코드 에디터 영역만 다크 |
| 백테스트 결과 | Light + 차트 영역 Dark | 차트 카드만 다크 배경 |
| 설정/프로필 | Light | 기본 SaaS 스타일 |
| 문서/도움말 | Light | 가독성 최우선 |

---

## 12. 다크↔라이트 전환부

두 테마가 한 페이지에 공존할 때 부드러운 그라데이션 전환을 사용:

```css
/* Light → Dark */
.transition-to-dark {
  height: 120px;
  background: linear-gradient(to bottom, #F8FAFC, #0B1120);
}

/* Dark → Light */
.transition-to-light {
  height: 120px;
  background: linear-gradient(to bottom, #0B1120, #FAFBFC);
}
```

---

## 13. 앰비언트 이펙트 (다크 섹션 전용)

대시보드와 다크 섹션에서 깊이감을 위한 배경 글로우:

```css
/* 인디고 글로우 블롭 */
.ambient-indigo {
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(99,102,241,0.06), transparent 70%);
  pointer-events: none;
}

/* 블루 글로우 블롭 */
.ambient-blue {
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(37,99,235,0.04), transparent 70%);
  pointer-events: none;
}
```

- 최대 2~3개만 사용 (과다 사용 금지)
- `pointer-events: none` 필수
- `overflow: hidden` 컨테이너 안에 배치

---

## 14. Tailwind CSS v4 매핑

프론트엔드 구현 시 Tailwind 토큰으로 매핑:

```ts
// tailwind.config.ts (참고용)
export default {
  theme: {
    extend: {
      colors: {
        // Light
        primary: { DEFAULT: '#2563EB', hover: '#1D4ED8', light: '#EFF6FF', 100: '#DBEAFE' },
        success: { DEFAULT: '#059669', light: '#D1FAE5' },
        destructive: { DEFAULT: '#DC2626', light: '#FEE2E2' },
        // Dark Dashboard
        dash: {
          bg: '#0B1120',
          surface: 'rgba(255,255,255,0.04)',
          'surface-elevated': 'rgba(255,255,255,0.07)',
          border: 'rgba(255,255,255,0.08)',
          text: '#EDEDEF',
          'text-muted': '#8A8F98',
          accent: '#6366F1',
          green: '#34D399',
          red: '#F87171',
        },
      },
      fontFamily: {
        heading: ['Plus Jakarta Sans', 'sans-serif'],
        body: ['Inter', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '14px',
        xl: '18px',
        pill: '20px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04)',
        'card-hover': '0 2px 8px rgba(0,0,0,0.08), 0 16px 40px rgba(0,0,0,0.06)',
      },
    },
  },
};
```

---

## 15. 디자인 의사결정 기록

| 결정 | 근거 | 대안 (기각) |
|------|------|------------|
| 라이트 메인 + 다크 대시보드 | 가독성/접근성 최적, 트레이딩은 다크가 표준 | 전체 다크 (장시간 피로), 전체 라이트 (트레이딩 분위기 부족) |
| Plus Jakarta Sans 제목 | 모던+프리미엄 느낌, Google Fonts 무료 | Space Grotesk (덜 프리미엄), Cormorant (금융과 안 맞음) |
| Inter 본문 | 가독성 최고, 가변 폰트 지원 | DM Sans (유사하나 가변폰트 미흡) |
| JetBrains Mono 데이터 | 탭룰러 피겨, 코드+숫자 겸용 | Fira Code (리가처 불필요) |
| Blue-600 (#2563EB) 프라이머리 | 금융 신뢰감, WCAG 대비 우수 | 골드 (과한 느낌), 시안 (접근성 약함) |
| Indigo-500 (#6366F1) 다크 액센트 | Blue와 구분되면서 프리미엄 | 동일 Blue (테마 구분 불가) |
| 8개 디자인 변형 비교 후 Final 선택 | F(Light SaaS) 88.5점 + H(Glass) 83.5점 조합 → 91.0점 | A~E, G 변형 (각각 결함 존재) |
