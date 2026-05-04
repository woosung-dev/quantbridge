# `reports/` — 자동 생성 dogfood / sprint retro / audit HTML 리포트

> **용도:** 시각화 우선 리포트 (HTML / 자동 dogfood 결과 / sprint pipeline 디자인) 보관소
> **상위 docs 표준 분류표:** [`../README.md`](../README.md)

## 현재 보유 (8 HTML + 1 sub-dir)

| 파일 / 디렉토리                                                                                                | 일자         | 주제                                                  | 형식    |
| -------------------------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------- | ------- |
| [`_template-h1-dogfood-retrospective.html`](./_template-h1-dogfood-retrospective.html)                         | template     | H1 dogfood 회고 dashboard 템플릿 (재사용)             | HTML    |
| [`2026-04-19-sprint-bcd-autonomous-retrospective.html`](./2026-04-19-sprint-bcd-autonomous-retrospective.html) | 2026-04-19   | Sprint B/C/D 자율 병렬 retro (PR #29/#30/#31)         | HTML    |
| [`2026-04-19-sprint-pipeline-skills-design.html`](./2026-04-19-sprint-pipeline-skills-design.html)             | 2026-04-19   | Sprint pipeline skill 설계 dashboard                  | HTML    |
| [`2026-04-20-autonomous-depth-chain-design.html`](./2026-04-20-autonomous-depth-chain-design.html)             | 2026-04-20   | autonomous depth chain 디자인 (FE Polish Bundle 패턴) | HTML    |
| [`2026-04-20-autonomous-depth-sprint-design.html`](./2026-04-20-autonomous-depth-sprint-design.html)           | 2026-04-20   | autonomous depth sprint 디자인                        | HTML    |
| [`2026-04-21-h1-closing-status-dashboard.html`](./2026-04-21-h1-closing-status-dashboard.html)                 | 2026-04-21   | H1 클로징 상태 dashboard                              | HTML    |
| [`2026-04-22-dogfood-start-dashboard.html`](./2026-04-22-dogfood-start-dashboard.html)                         | 2026-04-22   | testnet dogfood 시작 dashboard                        | HTML    |
| [`session-2026-04-18-sprint-8a-tier0.html`](./session-2026-04-18-sprint-8a-tier0.html)                         | 2026-04-18   | Sprint 8a Tier-0 session (pine_v2 foundation)         | HTML    |
| [`auto-dogfood/`](./auto-dogfood/)                                                                             | 2026-05-03 ~ | 자동 dogfood 일별 리포트 (HTML + JSON)                | sub-dir |

### `auto-dogfood/` 자동 일별 리포트

```
auto-dogfood/
├── 2026-05-03.html    # 자동 dogfood Day 0 (Sprint 26 dispatch 검증)
└── 2026-05-03.json    # 동일, JSON 원본 (machine-readable)
```

자동 dogfood Auto-Loop §0.5 first run (Sprint 27 시작 시점) 산출물. 향후 매일 추가 예정.

## 보는 방법 (HTML)

```bash
cd docs/reports
python3 -m http.server 8899 --bind 127.0.0.1
# 브라우저에서 http://localhost:8899/ 열기
```

또는 파일을 브라우저로 직접 드래그.

## 향후 추가 패턴

신규 리포트 추가 시 다음 명명 규칙:

```
reports/YYYY-MM-DD-<주제>.html       # 단발성 dashboard / retro
reports/auto-dogfood/YYYY-MM-DD.html # 자동 dogfood 일별
reports/auto-dogfood/YYYY-MM-DD.json # 동일, JSON 원본
```

예시 후보:

- `reports/2026-XX-XX-sprint28-retro.html` — Sprint 28 retro
- `reports/auto-dogfood/2026-05-04.html` — dogfood Day 1 자동 리포트
- `reports/2026-XX-XX-h1-closing-final.html` — H1 종료 final dashboard

## 활용 정책

- **HTML 리포트** — 자동 생성 권고 (gstack `/health`, `/retro`, `/qa-only` 등 skill 산출물). 수작업 변경 시 재생성 origin 명시.
- **JSON 원본** — `*.json` 은 reproducibility 용. 자동 도구가 갱신.
- **삭제 금지** — 시간순 trend 추적 (예: dogfood orders rejected 추세, sprint health score 변화)
- **template 파일 (`_template-*.html`)** — 신규 retro 작성 시 base. 직접 갱신 시 prefix 유지
