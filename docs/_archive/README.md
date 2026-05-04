# `_archive/` — Deprecated docs 보관소

> **정책:** 6개월+ 미참조 / sprint 종료 후 자연스럽게 이관 / **절대 삭제 금지**.
> 본 디렉토리의 모든 파일은 git history 보존 + 향후 reference 가능.

## 목적

- 활성 docs/ 트리에 떠도는 noise 제거 (stale plan, deprecated spec, 종료된 sprint prompt 등)
- 역사적 맥락 보존 — 향후 같은 패턴 재발 시 참조 가능
- 활성 ↔ archive 경계 명확화로 신규 sprint 시 confusion 회피

## 구조

```
_archive/
└── 2026-Q2-h1/                   # H1 (Sprint 1-19) 종료 시점 archive
    └── next-session/             # 12 stale next-session-*.md (Sprint 8b/8c/9/10/11/FE-01/Bundle 1/Bundle 2/B-C-D/testnet 등 plan prompt)
        └── INDEX.md              # 12 파일 한 줄 요약 + 원위치 + 추정 sprint
```

## 신규 archive 추가 시 (정책)

1. **이동만, 삭제 금지** — `git mv` 사용 (history 보존)
2. **redirect note 의무** — 이동된 파일 top 에 다음 1줄 추가:
   ```markdown
   > **ARCHIVED 2026-XX-XX:** 본 파일은 `docs/<원위치>` 에서 이동됨. <한 줄 사유>.
   ```
3. **INDEX.md 갱신** — `_archive/<period>/<category>/INDEX.md` 또는 `_archive/INDEX.md` 에 한 줄 등록
4. **docs/README.md 표준 분류표** 의 `_archive/` 행 cross-link 갱신 (필요 시)

## archive 분기 기준 (다음 분기 예상)

| 분기 디렉토리 | 시점                                          | 대상                                                                    |
| ------------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| `2026-Q2-h1/` | H1 종료 (Sprint 19 ~ Sprint 27 dogfood Day 1) | H1 sprint plan/prompt/spec 의 deprecated 항목                           |
| `2026-Q3-h2/` | H2 종료 (지인 Beta 5명 클로징)                | H2 Sprint plan/spec 의 deprecated, Monte Carlo / Optimizer 의 초기 plan |
| `2026-Q4-h3/` | H3 종료 (TV 커뮤니티 공개 + 첫 $1)            | Beta 운영 metric, 가격 실험 결과 archive                                |

## 비추: `_archive/` 안에 직접 새 파일 생성 금지

- archive 는 **이동 only** 디렉토리
- 신규 작성은 항상 활성 위치 (`dev-log/`, `superpowers/specs/`, `00_project/` 등) 에서 → 6개월 후 자연 이관
