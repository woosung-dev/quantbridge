# Step 0: `doc-coord-audit.py` 를 pytest 게이트에 배선한다

## 읽어야 할 파일

- `tools/scripts/doc-coord-audit.py` — 감사기 본체. 모드 3종(`--check` · `--dead-paths` · `--selftest`)
  과 `--baseline` · `--only` 가 234~252행 근처에 있다
- `apps/api/tests/scripts/test_ledger_vitals.py` — **이 디렉터리의 관용구 정본**
  (`subprocess.run` + `tmp_path` 임시 파일 + 인자 오버라이드)
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 같은 관용구의 두 번째 사례

## 배경

`doc-coord-audit.py` 는 2026-08-25 n10 이 만든 감사기다. 문서 좌표(줄 번호 인용)와 죽은 문서 경로를
잡는다. **그런데 아무도 그것을 자동으로 돌리지 않는다** — pre-commit 배선도, CI 스텝도 없다.

즉 지금 상태는 「감사기가 있다」이지 「감사가 돈다」가 아니다. 이 레포는 그 차이로
**「돌았다 ≠ 발화했다」** 를 반복해 겪었다.

★**`.github/workflows/**` 에 새 잡을 추가하지 마라.** 이유: [ADR-037] 제로베이스가 CI 표면을
의도적으로 좁혀 뒀고(「하네스 재추가는 문서화된 사고 1건 = 슬림 복귀 1건 규칙만 허용」),
잡 추가는 사용자·CONTROL 결정이다. **pytest 안에 배선하는 것이 이 레포의 확립된 선례다** —
`tests/scripts/` 의 기존 30개 파일이 전부 그 방식으로 셸/파이썬 스크립트를 판정한다.

## 작업

`apps/api/tests/scripts/test_doc_coord_audit.py` 를 신설한다.
**테스트 이름에 `doc_coord` 를 포함시켜라**(AC 가 `-k doc_coord` 로 잡는다).

### 레포 루트 경로 유도

★**`parents[N]` 을 이 문서에서 베끼지 마라 — 직접 세라.** 이 레포는 step 파일의 `parents[3]` 오기를
세션 6벌이 전건 교정한 적이 있다. `test_ledger_vitals.py` 의 유도식을 확인하고 같은 방식으로 써라.

### 테스트 3건 이상

1. `test_doc_coord_audit_check_passes_on_the_repository`
   `--check` 를 실제 레포에 대해 돌려 rc=0 을 단언한다(현재 실측 rc=0)
2. `test_doc_coord_audit_dead_paths_passes_on_the_repository`
   `--dead-paths` rc=0
3. `test_doc_coord_audit_selftest_proves_discriminating_power`
   `--selftest` rc=0 이고, **stdout 에 selftest 케이스 통과 표시가 1건 이상** 있다.
   ★단순 rc 단언만 두지 마라 — selftest 가 케이스 0건으로 조용히 통과하면 그 rc 는 무증거다

### ★판별력은 selftest 를 믿지 말고 직접 재라

n10 CONTROL 이 쓴 방법을 재사용해라: **`tmp_path` 에 위반을 심은 임시 문서를 만들어** 감사기를
그쪽으로 겨눠 rc≠0 을 확인하는 테스트를 추가한다. 감사기가 대상 경로를 인자로 못 받으면
**실레포 파일을 수정해 재지 마라** — 대신 그 사실(대상 고정)을 테스트 주석에 남기고,
selftest 의 케이스 수 단언으로 대체해라.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/scripts -k doc_coord -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/scripts -k doc_coord --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
python3 tools/scripts/doc-coord-audit.py --selftest
cd apps/api && uv run ruff check tests/scripts
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `subprocess` 호출에 **`timeout` 을 걸어라** — 이 디렉터리의 기존 테스트가 전부 그렇게 한다.
   무인 러너에서 행이 걸리면 재시도 한도를 태운다.
3. **rc 를 파이프로 읽지 마라** — `cmd | tail` 은 `cmd` 가 아니라 `tail` 의 rc 다.
   이 레포에서 10회 이상 재발했다. `subprocess.run(...).returncode` 를 직접 봐라.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`.github/workflows/**` 에 새 잡·새 스텝을 추가하지 마라.** 이유: [ADR-037] 재입힘 규칙.
- **`tools/scripts/doc-coord-audit.py` 의 판정 로직을 바꾸지 마라.** 이유: 이 step 은 **배선**이다.
  감사기가 red 를 내면 그것은 고칠 신호이지 감사기를 약화할 신호가 아니다.
- **실레포 문서 파일에 위반을 심어 판별력을 재지 마라**(심었다면 반드시 원복).
  이유: `docs/**` 는 CONTROL 소관이고 다른 lane 과 충돌한다.
- **`tests/common/**` · `tests/trading/**` · `src/**` 를 만지지 마라.** 이유: 다른 lane 의 소유 구역이다.
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
