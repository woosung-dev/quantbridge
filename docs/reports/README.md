# `reports/` — 자동 생성 dogfood / sprint retro / audit HTML 리포트

> **용도:** 시각화 우선 리포트 (HTML / 자동 dogfood 결과 / sprint pipeline 디자인) 보관소
> **상위 docs 표준 분류표:** [`../README.md`](../README.md)

## ★ 레포에 실제로 있는 것은 2개뿐이다

`.gitignore` 의 `docs/reports/*.html` 규칙이 이곳을 제외하고, 바로 뒤 `!` 두 줄이 템플릿과 `auto-dogfood/` 만 되살린다.
**그래서 여기 나열됐던 단발성 dashboard 8건은 레포에 없다** — 생성물이라 커밋되지 않았다.
필요하면 만든 회차의 커밋에서 찾아라.

| 파일 / 디렉토리                                                                        | 일자         | 주제                                      | 추적    |
| -------------------------------------------------------------------------------------- | ------------ | ----------------------------------------- | ------- |
| [`_template-h1-dogfood-retrospective.html`](./_template-h1-dogfood-retrospective.html) | template     | H1 dogfood 회고 dashboard 템플릿 (재사용) | ✅ 예외 |
| [`auto-dogfood/`](./auto-dogfood/)                                                     | 2026-05-03 ~ | 자동 dogfood 일별 리포트 (HTML + JSON)    | ✅ 예외 |

★★**새 HTML 리포트를 손으로 만들지 마라**(2026-08-15 사용자 지시). gitignore 되어 아무도 읽지 않는다.
회차의 결론은 `docs/status.md`·`docs/lessons.md`·`docs/dev-log/INDEX.md` 로 남긴다.
★**예외는 하나 — 사용자가 명시적으로 요청했을 때다**(2026-08-20 확인). 그때는 위 명명 규칙대로
만들고 그대로 둔다: gitignore 라 커밋되지 않고 **요청한 사용자의 로컬에서만** 열린다(보는 법 = 아래 §보는 방법).
아래 「향후 추가 패턴」은 **자동 생성 도구**(auto-dogfood)에만 적용된다.

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

- **HTML 리포트** — **자동 생성만**. 손으로 쓰지 않는다(위 ★★).
- **JSON 원본** — `*.json` 은 reproducibility 용. 자동 도구가 갱신.
- **삭제 금지** — 추적되는 2건(템플릿 · `auto-dogfood/`)에만 해당. 나머지 `*.html` 은 애초에 gitignore 라 「삭제」할 것이 없다
- **template 파일 (`_template-*.html`)** — 신규 retro 작성 시 base. 직접 갱신 시 prefix 유지
