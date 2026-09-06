# 아키텍처 다이어그램 (archify)

> **스펙(`*.archify.json`)이 정본**이고 `.html` 은 그 렌더 산출물이다. 노드의 `sources` 는 코드의 파일·줄을
> 가리키며 뷰어의 `SRC` 배지가 거기로 연결된다. 문서가 코드와 어긋나면 **코드가 맞다** — 스펙을 고쳐라.

| 스펙 | 타입 | viewBox | 무엇 |
| --- | --- | --- | --- |
| `system-runtime` | architecture | 1340×540 | 브라우저 → Next(인증) / FastAPI → Redis → Celery 워커 → Bybit 런타임 토폴로지 |
| `data-model` | architecture | 1380×540 | 24 테이블(앱 19 + Better Auth 5) · 스키마 3종 · FK 삭제 정책 |
| `repo-structure` | architecture | 1380×540 | 모노레포 최상위 → 앱 · 인프라 · 도구 · 문서 2단 지도 + 집행되는 경계 |
| `backtest-roundtrip` | sequence | 1340×560 | 백테스트 제출 → Celery → 결과 왕복 |
| `backtest-lifecycle` | lifecycle | 1340×566 | 백테스트 상태 머신 |
| `ohlcv-pipeline` | dataflow | 1340×530 | 거래소 → TimescaleDB hypertable → 백테스트 소비 |

## 재생성

archify 스킬(Claude Code `/archify`)의 CLI 로 만든다. 스펙을 고쳤으면 **검증 → deliver → 브라우저 실측**
3단을 다시 돈다. `<타입>` 은 위 표의 값이다(`diagram_type` 필드와 같다).

```bash
ARCHIFY=~/.claude/skills/archify/bin/archify.mjs
D=docs/architecture/diagrams
node $ARCHIFY validate <타입> $D/<이름>.archify.json --quality showcase --repo-root . --json
node $ARCHIFY deliver  <타입> $D/<이름>.archify.json $D/<이름>.html --quality showcase --repo-root .
node $ARCHIFY visual-check $D/<이름>.html --json
```

- `--repo-root .` 가 `sources` 의 **경로·줄 번호를 로컬 git 과 대조**한다. 파일을 옮기거나 줄이 밀리면
  스펙의 `sources.line` 을 함께 갱신해라 — 안 하면 validate 가 막는다.
- `visual-check` 는 1440×900 · 1600×1000 · 1920×1080 · 2048×1320 에서 containment 를 잰다.
  ★**뷰어는 세로 초과를 안 줄인다** — 폭 1340 대에서는 `viewBox` 세로를 **≤530~570** 으로 잡아라.
  이 표의 값이 실제로 통과한 조합이다.
- 새 다이어그램 기본값 — `quality_profile = "showcase"` · 노드 ≤ 12 · 자동 라우팅 우선 ·
  `labelAt`·`via` 는 **검증기가 요구할 때만** 하나씩 붙인다.
- `dataflow`·`lifecycle`·`sequence` 의 sublabel 은 7px 고정이라 1340 폭에서는 읽히지 않는다 — 넣지 마라.

## 이 문서의 출처

2026-09-04 archify 회차의 재생성 런북이 스태시에만 남아 있던 것을 2026-09-06 에 되살리면서,
표를 그때(3장)가 아니라 **오늘(6장)** 기준으로 다시 쟀다. 원문 = `refs/stash-archive/00`.
