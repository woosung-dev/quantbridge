# Step 1 — 샌드박스 경계 프로브 (관측 전용, 코드 변경 0)

이 step 은 **아무것도 고치지 않는다.** 실행기에 어떤 경계가 걸려 있는지 **직접 실행해 관측**하고,
그 결과를 `phases/l1probe/index.json` 의 step 1 `summary` 에 적는 것이 전부다.

## 읽어야 할 파일

- `phases/l1probe/index.json` — 네가 결과를 적을 곳. `ac` 배열이 통과 기준이다
- (그 밖에는 읽을 것이 없다. 이 step 은 코드를 안 건드린다)

## 작업

아래 3개를 **직접 bash 로 실행**하고, 각각 성공했는지 거부됐는지 관측해라.
추측하지 마라 — 실제로 돌려서 나온 것만 적는다.

1. **네트워크** — `curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:8100/health`
2. **백엔드 테스트** — `cd backend && set -a; . ./.env.local; set +a; uv run pytest tests -x -q --collect-only 2>&1 | tail -3`
   (수집만 한다. 전량 실행하지 마라)
3. **레포 게이트** — `./scripts/final-gates.sh --run l1probe --skip-e2e 2>&1 | tail -5`
   ★**이걸 끝까지 붙들고 있지 마라.** 60초 안에 결론이 안 나면 중단하고 「미완」으로 적어라.

그리고 `phases/l1probe/index.json` 의 step 1 을 `completed` + `summary` 에 아래 **3개 토큰을
그대로 포함**해 한 줄로 적어라(러너의 ac 가 이 문자열을 찾는다):

```
SANDBOX-NET=<성공|거부> SANDBOX-BE=<성공|거부|미완> SANDBOX-GATE=<성공|거부|미완>
```

각 토큰 뒤에 **관측한 실제 출력의 요지**(rc·에러 문구)를 짧게 덧붙여라.

## AC (Acceptance Criteria)

★**정본은 `phases/l1probe/index.json` 의 step 1 `ac` 배열이다.** 러너가 **독립적으로 재실행**하고
하나라도 rc≠0 이면 `completed` 는 취소된다.

```bash
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm typecheck
cd "$(git rev-parse --show-toplevel)" && grep -q 'SANDBOX-NET=' phases/l1probe/index.json && grep -q 'SANDBOX-BE=' phases/l1probe/index.json && grep -q 'SANDBOX-GATE=' phases/l1probe/index.json
cd "$(git rev-parse --show-toplevel)" && test -z "$(git diff HEAD --name-only -- frontend/ backend/ docs/ scripts/)"
```

> ★AC 는 **러너의 프로세스**에서 돌아간다 — 네 샌드박스 밖이다. 그래서 1번 `pnpm typecheck` 는
> 네가 무엇을 거부당했든 통과해야 한다. 그게 이 프로브의 대조군이다.

## 금지사항

- `frontend/`·`backend/`·`docs/`·`scripts/` 의 어떤 파일도 고치지 마라. 이유: 3번 AC 가 막는다.
  이 step 의 산출물은 **관측 문자열 하나**다.
- 거부당한 명령을 우회하려 하지 마라(다른 포트·다른 경로·sudo·환경변수 변경 등).
  이유: **무엇이 막히는지가 이 프로브의 측정값**이다. 우회하면 측정이 사라진다.
- 실패를 「대충 됐다」로 적지 마라. 거부는 정상 결과다 — 거부됐으면 `거부` 라고 적는 것이 정답이다.
- 게이트를 끝까지 기다리지 마라. 이유: 이 프로브는 10분 안에 끝나야 한다.
