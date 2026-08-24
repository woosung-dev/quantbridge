# Step 0: 좌표 감사기 신설 — 드리프트를 기계가 재게 한다

## 읽어야 할 파일

- `DESIGN.md` — 특히 §4.2 · §4.3 · §10.2 · §10.6 (`globals.css` 좌표가 몰려 있다)
- `apps/web/src/styles/globals.css` — 인용 대상(4,000줄 규모)
- `apps/web/e2e/design-canon-responsive.spec.ts` — 주석에 좌표를 든다
- `tools/scripts/ledger-vitals.sh` — 이 레포의 「작은 검사기」 관용구 참고(출력·rc 스타일)

## 배경

`DESIGN.md` 와 `design-canon-responsive.spec.ts` 는 `globals.css` 를 **줄 번호로** 인용한다.
그런데 `globals.css` 는 4,000줄이 넘고 **어떤 편집이든 그 아래 좌표를 전부 민다.**
2026-08-24 실측에서 `DESIGN.md` 의 인용 다수가 이미 다른 줄을 가리키고 있었다 —
예컨대 `--sidebar-w: 232px` 는 실제로 169행인데 문서는 168행이라 적었다.

★**이 회차는 좌표를 재측정하지 않는다.** 재측정은 같은 병의 N번째 치료이고 다음 CSS 편집에서 또
밀린다. **앵커(선택자·토큰명·센티넬)로 전환**해 드리프트 종(種) 자체를 없앤다. 그러면 감사기는
「`globals.css` 를 줄 번호로 인용한 곳이 0인가」만 재면 된다.

## 작업

`tools/scripts/doc-coord-audit.py` 를 신설한다. **python 으로 써라** — 이 레포의 셸 검사기가
6회 무증거를 냈다([LESSON-124]). 판정은 **rc** 로 낸다(0=통과, 1=위반, 2=사용법 오류).

### 모드 4종

| 플래그 | 하는 일 |
| --- | --- |
| `--check` | 대상 문서에서 **줄 번호 인용**을 찾아 **0건**이면 rc=0 |
| `--check --baseline` | 현재 위반 수를 **동결 파일과 대조**한다(정확 동등). 착수 시점의 red 를 기록하는 용도 |
| `--check --only <경로>` | 그 파일만 검사 |
| `--dead-paths` | 레포에 **존재하지 않는 문서 경로**를 참조하는 곳을 찾아 0건이면 rc=0 |
| `--selftest` | ★**판별력 증명.** 합성 입력에 위반을 심어 잡히는지, 정답 형태는 안 잡히는지 확인 |

### 검사 규칙

**⑴ 줄 번호 인용** — 다음 두 모양을 위반으로 잡는다.
- `globals.css:123` / `globals.css:123-130` (백틱 안팎 무관)
- `globals.css` 를 문맥으로 둔 채 쓰는 단독 `` `:123` `` / `` `:123-130` ``

**⑵ 검사 대상 파일** — `DESIGN.md` 와 `apps/web/e2e/design-canon-responsive.spec.ts` **둘로 시작한다.**
★**가드레일 4축(`CONTEXT.md`·`AGENTS.md`·`apps/api/AGENTS.md`·`apps/web/AGENTS.md`)은 대상에서
제외하고, 제외 이유를 코드 주석에 남겨라** — 그 파일들은 lane 이 수정할 수 없어 검사해도 고칠 수
없다(CONTROL 후속 과제). 대상 목록은 스크립트 상단 상수로 두어 나중에 넓힐 수 있게 해라.

**⑶ 죽은 문서 경로**(`--dead-paths`) — `docs/`·`apps/web/src`·`apps/api/src` 의 주석·산문이
참조하는 마크다운 경로 중 **레포에 없는 것**을 잡는다. 알려진 것: `frontend/AGENTS.md` ·
`frontend.md` · `nextjs-shared.md`(ADR-026/027/029 로 병합·이동돼 사라진 이름들).
**건수는 네가 직접 세라** — 이 문서의 숫자를 옮기지 마라.

### `--selftest` 는 필수다

임시 디렉터리에 합성 파일을 만들어 다음을 확인하고, 하나라도 어긋나면 rc=1:
- **양성** — `globals.css:999` 를 심으면 잡힌다
- **양성** — 단독 `` `:999` `` 를 `globals.css` 문맥에서 심으면 잡힌다
- **음성** — 앵커 형태(`` `globals.css` 의 `--sidebar-w` 선언 ``)는 **안 잡힌다**
- **음성** — 무관한 파일의 줄 번호(`execute.py:44`)는 **안 잡힌다**

★이유: 「0건이니 통과」는 **대상에 닿지 않아도 참**이다. 이 레포는 그 함정을 여러 번 밟았다.

### 착수 시점 동결

`--check --baseline` 이 참조할 동결 파일(예: `tools/scripts/doc-coord-audit.baseline.json`)에
**현재 위반 수를 실측해 기록**해라. 그 수가 **0 이면 안 된다** — 0 이면 검사기가 대상에 안 닿은 것이다.
`summary` 에 파일별 분포를 남겨라. step 1·2 가 그것을 소비한다.

## Acceptance Criteria

```bash
test -f tools/scripts/doc-coord-audit.py
python3 tools/scripts/doc-coord-audit.py --selftest
python3 tools/scripts/doc-coord-audit.py --check --baseline
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `--check`(baseline 없이)를 돌려 **rc=1** 이 나오는지 확인해라 — 지금은 위반이 있으므로 red 가
   정상이다. green 이면 검사기가 아무것도 안 보고 있는 것이다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`DESIGN.md` 나 spec 을 이 step 에서 고치지 마라.** 이유: 이 step 의 산출은 검사기다. 수리는 step 1 부터다.
- **셸로 검사기를 쓰지 마라.** 이유: [LESSON-124] — 이 레포의 셸 검사기가 6번 무증거를 냈다.
- **판정 명령에 파이프를 붙여 rc 를 흘리지 마라.** 이유: 이 레포에서 10회 이상 재발했다.
- **가드레일 4축을 검사 대상에 넣지 마라.** 이유: lane 이 그 파일을 수정할 수 없어 red 를 못 푼다.
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축을 수정하지 마라.**
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
