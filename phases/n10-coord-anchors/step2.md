# Step 2: e2e spec 주석 좌표 + 죽은 문서 경로 참조

## 읽어야 할 파일

- `apps/web/e2e/design-canon-responsive.spec.ts` — 주석이 `globals.css` 줄 번호를 든다
- `tools/scripts/doc-coord-audit.py` — step 0 이 만든 감사기
- 이전 step 들의 `summary`

## 배경

**⑴ spec 자신이 낡은 좌표를 들고 있다.** `design-canon-responsive.spec.ts` 는 이 레포에서 셸 경계를
실측 집행하는 spec 인데, 그 **주석**이 `globals.css` 줄 번호를 인용하고 그 다수가 밀려 있다.
주석은 어떤 단언도 읽지 않으므로 **영원히 red 가 안 난다** — 문서가 아니라 코드 안에 있는 같은 병이다.

**⑵ 존재하지 않는 문서를 가리키는 참조가 남아 있다.** ADR-026/027/029 를 거치며 `frontend/AGENTS.md` ·
`frontend.md` · `nextjs-shared.md` 가 병합·이동돼 사라졌는데, `docs/` 와 `apps/web/src` 주석이
아직 그 이름을 쓴다. 좌표가 죽으면 다음 사람이 근거를 못 찾는다.

## 작업

### ⑴ spec 주석을 앵커로

step 1 과 같은 원칙이다 — 선택자·토큰명·센티넬로 바꾼다. **주석만 바꾸고 단언·셀렉터·수치는 건드리지 마라.**
그 spec 의 판정 로직을 바꾸면 이 회차의 범위를 넘는다.

### ⑵ 죽은 문서 경로 정정

`--dead-paths` 가 잡는 참조를 **현재 실재하는 경로**로 바꾼다.

| 죽은 이름 | 지금 어디 |
| --- | --- |
| `frontend/AGENTS.md` | `apps/web/AGENTS.md` (ADR-029 모노레포 재배치) |
| `frontend.md` · `nextjs-shared.md` | `apps/web/AGENTS.md` 로 병합됨 (ADR-026/027) |

★**하위 절 번호가 함께 죽은 것이 있다** — 예컨대 `frontend.md §3.2` 의 `§3.2` 는 지금 문서에 없다
(현 `apps/web/AGENTS.md` §3 은 하위 번호를 안 쓴다). 이런 것은 **살아 있는 좌표로 바꾸거나**
(`apps/web/AGENTS.md` §3 의 해당 규칙) 절 번호를 빼라. **없는 번호를 그대로 옮기지 마라.**

★**`apps/web/AGENTS.md` 자체는 수정하지 마라** — 가드레일 4축이라 lane 권한 밖이다.
그 파일을 고쳐야 하는 것이 나오면 `summary` 에 적어 CONTROL 에 넘겨라.

### ⑶ 곁다리 1건

`apps/web/src/lib/auth-server.ts` 의 머리 주석이 `getServerAuth()` 「호출부 3곳」이라 적는데
실제 호출부 수가 다르다. **직접 세서** 주석을 실측에 맞춰라(개수와 경로 둘 다).

## Acceptance Criteria

```bash
python3 tools/scripts/doc-coord-audit.py --selftest
python3 tools/scripts/doc-coord-audit.py --check
python3 tools/scripts/doc-coord-audit.py --dead-paths
cd apps/web && pnpm exec biome check .
cd apps/web && pnpm exec tsc --noEmit
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **앵커 실재 확인** — 새로 쓴 앵커·경로가 실제로 존재하는지 grep 으로 확인해라.
3. `summary` 에 ⑴/⑵/⑶ 각각의 처리 건수와, **CONTROL 로 넘긴 가드레일 항목**을 적어라.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **spec 의 단언·셀렉터·경계 수치를 고치지 마라.** 이유: 이 step 은 주석 좌표 전환이다.
  그 spec 의 판정을 바꾸면 화면 계약이 조용히 움직인다.
- **가드레일 4축(`CONTEXT.md`·`AGENTS.md`·`apps/api/AGENTS.md`·`apps/web/AGENTS.md`)을 수정하지 마라.**
  이유: lane 권한 밖이다. 필요하면 `summary` 로 CONTROL 에 넘겨라.
- **죽은 경로를 「비슷한 것」으로 추측해 바꾸지 마라.** 이유: 근거 좌표가 틀리면 없느니만 못하다.
  확신이 안 서면 그 항목을 `summary` 에 적고 남겨라.
- **`docs/status.md`·`docs/backlog.md` 를 수정하지 마라.**
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
