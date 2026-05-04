# `superpowers/reports/` — 자동 생성 리포트 (architecture / audit / x1x3 final)

> **총 파일:** 3개 · **기간:** 2026-04-23 (단일 일자)
> **상위 INDEX:** [`../INDEX.md`](../INDEX.md)

## 3 리포트

| 파일                                  | 형식     | 주제                                              | 사이즈 | 출처                             |
| ------------------------------------- | -------- | ------------------------------------------------- | ------ | -------------------------------- |
| `2026-04-23-architecture-survey.html` | HTML     | H1 architecture 종합 survey (다이어그램 + 테이블) | ~39KB  | architecture audit script (자동) |
| `2026-04-23-documentation-audit.md`   | Markdown | docs/ 정합성 audit (171 파일 시점)                | ~10KB  | 자동 (LinkChecker + 정합성 검증) |
| `2026-04-23-x1x3-final.md`            | Markdown | Sprint X1+X3 5 워커 × 4 evaluator 최종 합산       | ~9KB   | 자동 (review 20 파일 합산)       |

## 활용 정책

- **HTML 리포트** (`*.html`) — 브라우저로 직접 확인. 갱신 시 자동 재생성 권고.
- **Markdown 리포트** — git diff 추적 가능. 사용자 직접 갱신 시 자동 생성 origin 명시.
- 신규 리포트 (예: dogfood retro, security audit) 는 `docs/audit/`, `docs/reports/` 의 활성 디렉토리에 생성. 본 디렉토리는 H1 archive 로 보존.

## Cross-link

- `2026-04-23-x1x3-final.md` ↔ [`../reviews/`](../reviews/) (20 review 합산 origin)
- `2026-04-23-documentation-audit.md` ↔ 향후 docs cleanup 시 reference (현재 Sprint 27 + dogfood Day 1 cleanup 의 baseline)
- `2026-04-23-architecture-survey.html` ↔ [`../../04_architecture/architecture-conformance.md`](../../04_architecture/architecture-conformance.md) (15 항목 정합성 audit 영구 체크리스트)
