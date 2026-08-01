# Legal Temporary Runbook (Sprint 11 Phase B)

> **Created:** 2026-04-25 (H2 Sprint 11 Phase B)
> **Owner:** 본인
> **Replaced at:** H2 말 (~2026-06-30) 정식 변호사 검토본 (D-5 A 안)

---

## 배경

H2 Beta 단계에서 Disclaimer / Terms / Privacy 가 법적 효력을 가지려면 **한국 변호사 검토** 가 필수다. 그러나 H2 Sprint 11 (Beta 오픈 직전) 까지 변호사 계약·검토 절차를 완료하기 어려움. 따라서 **임시 템플릿 (D-5 B 안)** 으로 시작하되, 다음 원칙을 준수한다:

1. **법적 효력 제한 고지 배너** 를 전 페이지 상단에 항상 노출.
2. 3 개 법무 페이지 (Disclaimer / Terms / Privacy) 본문 최상단에 동일 경고 블록 포함.
3. H2 말 정식 교체를 계획·예산으로 확정 (D-5 A 안, $500~$1,500).

---

## 임시 템플릿 출처

- **Disclaimer**: termly.io 무료 generator → AI (Opus) 검토 → 아시아-태평양 지역 특화 문구 추가
- **Terms of Service**: termly.io 무료 generator → 준거법 대한민국, 관할 서울중앙지법 명시
- **Privacy Policy**: termly.io + 한국 개인정보보호법 필수 고지 항목 (보존 기간, 제3자 처리자)

> **주의:** termly.io generator 출력은 미국 법 기준. 한국 개인정보보호법·전자상거래법·전자금융거래법의 필수 고지 항목을 전부 커버하지 못한다. 정식 법무 검토 전까지 Beta 사용자에게 충분한 투명성 유지 — **수집 데이터·제3자 처리자 전체 명시 + 연락처 제공**.

---

## 변경 이력

| 시점        | 변경                     | 비고                                         |
| ----------- | ------------------------ | -------------------------------------------- |
| 2026-04-25  | 초판 (Sprint 11 Phase B) | termly 기반 한/영 혼용. Beta 오픈 동시 배포. |
| _H2 말 TBD_ | 정식 변호사 검토본 교체  | D-5 A 안 — 한국 변호사 스타트업 패키지.      |

---

## H2 말 정식 교체 절차 (D-5 A 안)

### 1. 변호사 선정

- **후보:** 로앤컴퍼니 / 법무법인 지평 / 세종 스타트업팀 등 한국 로컬 스타트업 패키지 (~$500-1,500/건)
- **대안:** 글로벌 (LegalZoom, Stripe Atlas) — 한국 법 커버 부족, 비권장
- **선정 기준:**
  - 암호화폐/핀테크 경험
  - 영문 약관 병행 제공
  - 개인정보보호법·전자금융거래법·특금법 커버

### 2. 검토 범위

- Disclaimer: 투자자문 부인·손해배상 제한 유효성
- Terms: 이용자격, 금지행위, 준거법·관할, 해지 조항
- Privacy: 개정 개인정보보호법 (2023~) 준수, 위치정보법 영향, 개인정보 영향평가 여부
- 추가: 거래소 API Key 보관·처리 관련 특금법·자금세탁방지 고지

### 3. 배포

- 정식본 확정 → 3 개 FE 페이지 교체 + `LegalNoticeBanner` 문구 수정 (`"법무 임시 — 정식 배포본"` 제거)
- 기존 Beta 사용자에게 이메일 알림 + 대시보드 공지 (최소 7 일 전)
- Git tag `legal-v1.0-formal` 로 정식본 이정표 기록

---

## 현재 구현 파일

| 경로                                              | 역할                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------ |
| `frontend/src/app/disclaimer/page.tsx`            | 면책조항                                                                 |
| `frontend/src/app/terms/page.tsx`                 | 이용약관                                                                 |
| `frontend/src/app/privacy/page.tsx`               | 개인정보 처리방침                                                        |
| `frontend/src/components/legal-notice-banner.tsx` | 전역 고지 배너                                                           |
| `frontend/src/lib/legal-links.ts`                 | 링크 상수                                                                |
| `frontend/src/app/layout.tsx`                     | 배너 삽입 지점 (`<body>` 최상단)                                         |
| `frontend/src/proxy.ts`                           | `/disclaimer`, `/terms`, `/privacy` 를 public route + geo-exempt 로 등록 |

---

## 모니터링 (follow-up)

정식 교체 전까지 아래 메트릭이 유의미해지지 않도록 관찰:

- `/disclaimer`, `/terms`, `/privacy` 페이지뷰 카운트
- 법무 관련 사용자 지원 요청 카운트 (이메일)
- 약관 위반으로 인한 계정 정지 건수 (현재 0, 발생 시 정식 문구 가속화)

---

## Rollback

임시 템플릿 자체를 내릴 일은 거의 없음. 대신:

- 특정 조항에서 법적 이의가 들어오면 → 해당 섹션 주석 처리 + PR 후 재검토
- 전체 배너 문구가 사용자 경험을 해친다고 판단되면 → `LegalNoticeBanner` 문구 조정 (너비/색상/옵션 opt-out), 페이지는 유지

배너 자체 비활성화는 **법무 위험 증가** 이므로 금지.
