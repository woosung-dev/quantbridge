# Step 0: follow-config-and-cursor

## 읽어야 할 파일

- `tools/scripts/soak-logs-follow.sh` — **이번 테스트의 대상**. 특히 `:82-205`
  (`_is_timestamp` · `_validate_run_config` · `_append_log` · `_write_cursor` · `_valid_cursor` ·
  `_rotate_if_needed` · `_consume_logs` · `_run`)과 `:475-506`(dispatch 인자 개수 계약)
- `apps/api/tests/scripts/test_soak_observe.py:19-31` — `tmp_path` 가짜 레포 관용구

## 배경

[BL-619](🟡 부분) — **라이브 파이프라인이 한 세션에 ~17분 멈췄고 뿌리를 모른다.** 그 부검을
가능하게 하려고 2026-08-08 에 서버에 올린 것이 이 팔로워다. ★**그것은 Trigger 를 충족
가능하게 만든 것이지 뿌리를 안 것이 아니다** — 닫는 조건은 재관측 부검 그대로다.

⇒ **이 관측기가 회전·커서를 잘못 판정하면 부검 자체가 거짓이 된다.**
쓰레기 커서를 `--since` 로 넘기면 docker 가 5초 실패 루프에 빠지고, 커서가 전진하지 않으면
`docker restart` 뒤 로그가 처음부터 다시 들어와 **정지 구간이 두 번 세어진다.**
지금 이 파일의 테스트는 0건이다.

★**이 lane 은 「루프를 띄우고 죽여야 하는」 유일한 lane 이다** — `_run` 은 무한 루프다.
아래 방식을 그대로 따라라. 시간을 늘리지 말고 **경계 조건을 관측해서** 끝내라.

## 작업

`apps/api/tests/scripts/test_soak_logs_follow.py` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식)

`LOG_DIR="${ROOT}/.soak/logs"` 는 **env 로 못 바꾼다.** 그래서 `tmp_path` 가짜 레포에 복사한다.

```
tmp/tools/scripts/soak-logs-follow.sh   ← 진짜 파일 복사
tmp/bin/docker                          ← 스텁: argv 를 기록하고 정해진 줄들을 찍은 뒤 종료
tmp/.soak/logs/                         ← 대상이 스스로 만든다 (미리 만들지 마라 — 케이스 1이 그것을 잰다)
```

★**`--install`/`--uninstall`/`--status` 는 실행하지 마라** — `systemctl --user`·`launchctl`
로 실행자의 진짜 서비스를 건드린다. 이 step 이 부르는 것은 **`run` 과 인자 계약**뿐이다.

**루프를 끝내는 법** — 스텁 `docker` 는 줄을 찍고 **종료**한다. 그러면 `_consume_logs` 가
돌아오고 대상은 `=== [follow] detached …` 를 로그에 쓴 뒤 `sleep ${QB_FOLLOW_RECONNECT_SEC}`
로 들어간다. 그래서:

1. `QB_FOLLOW_RECONNECT_SEC` 를 **크게**(예: 300) 준다 — 두 번째 attach 가 없어야 관측이 결정론이다
2. `subprocess.Popen` 으로 띄우고 **로그 파일에 `detached` 마커가 나타날 때까지** 폴링한다
   (상한 ~15초, 간격 0.05초)
3. `proc.terminate()` → `proc.wait(timeout=…)` 로 회수한다. ★**좀비를 남기지 마라**
4. 그 뒤에 파일들을 읽어 단언한다

### 최소한 이 여섯을 덮어라 (케이스 ≥6)

1. ★**설정 검증은 루프 **전**이다** — `QB_FOLLOW_MAX_BYTES=abc` 로 `run` 하면 **rc=1** 이고
   stderr 에 그 이름이 실린다. ★그리고 **`.soak/logs/` 디렉터리가 만들어지지 않았다**
   (`mkdir -p` 는 검증 뒤다). `QB_FOLLOW_KEEP=0` 과 `KEEP=x` 도 같은 축으로 각각 한 줄.
   ★이 케이스들은 **`Popen` 없이 `subprocess.run` 으로** 끝난다(루프에 안 들어간다)
2. **dispatch 인자 계약** — `run x` · `--status x` · `--help x` 는 rc=1 이고,
   인자 없음(`''`)은 usage 를 **stderr** 로 내며 rc=1, 알 수 없는 인자도 rc=1
3. ★**커서를 안 쓰는 경우** — 커서 파일이 없거나 **쓰레기**(`not-a-time`)면 docker 인자에
   `--since` 가 **없다**. 유효한 RFC3339 Z 값이면 `--since <그 값>` 이 **있다**.
   ★두 방향을 다 재라 — 「없다」만 재면 docker 를 아예 안 불러도 참이다
4. ★**커서 전진** — 스텁이 `2026-08-20T01:02:03Z 어떤 로그` 형태 줄들을 내면 커서 파일에
   **마지막 타임스탬프**가 남는다. ★타임스탬프 **없는** 줄만 내면 커서 파일이 **생기지 않는다**
   (`_consume_logs` 는 첫 필드가 시각일 때만 커서를 쓴다)
5. ★**회전** — `QB_FOLLOW_MAX_BYTES` 를 작게(예: 200) 주고 `worker-follow.log` 를 그보다 크게
   미리 채워 두면, attach 직전 회전이 일어나 ⑴ `worker-follow.log.1` 이 생기고
   ⑵ 새 본체에 `rotated` 마커 줄이 있고 ⑶ **`KEEP` 을 넘는 세대는 사라진다**
   (`.1`~`.KEEP` 을 미리 만들어 두고 `.KEEP+1` 이 안 생기는지 재라)
6. ★**양성 대조 — 스텁이 실제로 불렸다.** 3·4·5 에서 docker 기록 파일이 존재하고
   그 첫 인자가 `logs` 이고 마지막 인자가 `QB_WORKER_CONTAINER` 값임을 함께 단언해라

★**시간에 기대지 마라** — `sleep` 을 단언에 쓰지 말고 **파일이 나타나는 것**을 폴링해라.
간헐 red 는 이 lane 에서 가장 나오기 쉽다. 폴링 상한을 넘기면 `pytest.fail` 로 **명확히**
죽여라(조용한 skip 금지).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_logs_follow.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_logs_follow.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**AC 를 3회 연속 돌려 전부 green 인지 확인해라** — 이 lane 은 프로세스를 띄우므로
   간헐성이 붙기 쉽다. 한 번이라도 red 면 폴링 상한이 아니라 **관측 대상**을 바꿔라
3. ★**남은 프로세스가 없는지 확인해라** — `pgrep -f soak-logs-follow` 가 0건이어야 한다
4. `summary` 에 폴링으로 관측한 **종료 마커**와 상한값을 남겨라

## 금지사항

- `tools/scripts/soak-logs-follow.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**`--install`/`--uninstall`/`--status` 실행 금지.** 이유: `systemctl --user`·`launchctl` 로
  **실행자의 진짜 서비스**를 건드린다(서버에서 도는 유닛과 같은 Label 이다)
- ★**진짜 `docker` 를 부르지 마라** — PATH 스텁이 없으면 진짜 워커 컨테이너에 `logs -f` 가
  붙어 **테스트가 끝나지 않는다**
- ★**레포의 `.soak/` 를 건드리지 마라** — 가짜 레포 안에서만 돈다. 진짜 경로를 겨누면
  소크 앵커와 커서를 덮어쓴다
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
