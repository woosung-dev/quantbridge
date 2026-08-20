# Step 1: disk-state-and-rc

## 읽어야 할 파일

- `tools/scripts/disk-guard.sh` — 상태 파일(105~119행) · `_check_freshness`(225~268행) ·
  `_status`(270~297행) · 종료 코드 규약(20~22행)
- `tools/scripts/lib/notify-telegram.sh` — `QB_NOTIFY_CMD` 주입 seam 의 계약
- `apps/api/tests/scripts/test_disk_guard.py` — **앞 step 이 만든 파일. 여기에 이어 붙인다**

## 배경

이 스크립트의 종료 코드 규약은 특이하다 — ★**디스크가 임계를 넘었다는 사실은 rc 로 새어나오지
않는다.** rc=1 은 「**감시자 자신이 실패**」(알림 전송 실패 · df 판독 실패)만 뜻한다.
그래야 systemd 의 빨간불이 「경보가 깨졌다」 하나만 뜻한다. 이 비직관적 규약이
테스트로 고정돼 있지 않으면 다음 사람이 「WARN 이면 rc=1」로 바꿔 놓는다.

그리고 순서 계약이 하나 더 있다 — ★**알림을 먼저 쏘고 상태를 나중에 저장한다.**
디스크가 꽉 차면 상태 파일 쓰기부터 실패하므로, 순서를 뒤집으면 정작 알려야 할 순간에
조용히 죽는다.

「설치본 신선도」는 [BL-737] 실사고에서 왔다 — 2026-08-13 재배치 후 soak-watch 가
**41시간 동안** 타이머는 정상 waiting 인 채 서비스만 rc=127 로 죽어 있었다.
유닛에는 **설치 시점의 절대경로가 구워진다.**

## 작업

`apps/api/tests/scripts/test_disk_guard.py` 에 **상태 파일 · 주입 seam · rc · 신선도**를
이어 붙여라. 앞 step 의 스텁/env 헬퍼를 그대로 재사용한다(새 헬퍼 모듈 금지).

비-dry-run 은 `QB_DISK_NOTIFY_CMD` 로 실제 발송을 대체한다. 본문은 그 명령의 **stdin** 으로
들어온다(`notify-telegram.sh` 의 `printf '%s\n' "${body}" | ${QB_NOTIFY_CMD}`).
받은 본문을 파일에 적고 종료 코드를 마음대로 정하는 sh 스텁을 tmp 에 만들어라.

### 최소한 이 넷 + 앞 step 6건 = 10건을 채워라

상태 파일 · 주입 seam:

1. **`--dry-run` 은 상태 파일을 쓰지 않는다** — WARN 전이인데도 파일이 안 생긴다
   (앞 step 의 모든 케이스가 이 사실에 기대고 있다. 여기서 그것을 못박는다)
2. **비-dry-run 발화 성공** — 주입 명령이 본문을 받고, 상태 파일에 `LEVEL=WARN` +
   `NOTIFIED_DATE=<스텁이 고정한 오늘>` 이 쓰인다. rc=0
3. ★**알림 전송 실패 → rc=1 이고 `NOTIFIED_DATE` 가 갱신되지 않는다** (주입 명령이 exit 1).
   ★이때도 **`LEVEL` 은 갱신된다** — 지금 스크립트가 무엇을 하는지 읽고 그대로 고정해라.
   이것이 「보냈다고 거짓 기록하지 않는다」의 관측면이다
4. **OK 유지(무발화) 에서도 상태 파일은 쓰인다** — 발화 없이도 `LEVEL=OK` 가 기록된다

rc · 인자 계약:

5. **`df` 판독 실패 → rc=1** (스텁 `df` 가 빈 출력을 내거나 사용률 칸이 숫자가 아닐 때).
   stderr 에 `df 판독 실패`
6. **`QB_DISK_WARN_PCT` 가 숫자가 아니면 rc=1** — stderr 에 `숫자가 아니다`
7. **알 수 없는 인자 → rc=1** · **`--help` → rc=0** 이고 stdout 에 사용법이 실린다

설치본 신선도(`--status`):

8. **유닛이 없으면 rc=1** 이고 stdout 에 `설치된 유닛이 없다`
9. ★**`ExecStart` 가 지금 이 파일이 아니면 rc=1** — `XDG_CONFIG_HOME` 아래
   `systemd/user/dev.quantbridge.disk-guard.service` 를 손으로 만들고 `ExecStart=/bin/bash
/엉뚱한/경로/disk-guard.sh` 를 넣어라. **[BL-737] 41시간 침묵의 재현이다**
10. **양성 대조 — 유닛 2벌이 모두 옳으면 그 축은 rc 에 기여하지 않는다.**
    `ExecStart` 가 진짜 `SCRIPT` 경로이고, 알람 유닛의 env 파일이 실재하면
    신선도 판정이 통과한다(전체 rc 는 df 판독 성공 여부만 남는다 → rc=0)

★9·10 케이스는 `systemctl` **스텁을 함께 둬라.** ubuntu(=CI)에는 진짜 `systemctl` 이 있고
macOS 에는 없어서, 스텁 없이는 로컬과 CI 가 다른 경로를 탄다. 스텁은 아무것도 하지 않고
exit 0 이면 된다(`_status` 는 조회 실패를 `|| echo` 로 흡수한다).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_disk_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_disk_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **rc 를 파이프로 읽지 마라.** `subprocess.run(...).returncode` 를 직접 본다 —
   이 레포는 셸에서 `| tail` 이 rc 를 삼켜 정반대 판정을 낸 사고가 6번 있다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/disk-guard.sh` · `tools/scripts/lib/notify-telegram.sh` 를 **수정하지 마라**
- **`--install` / `--uninstall` 을 실행하지 마라** — 실행자의 systemd user 디렉터리에 쓰고
  `systemctl --user enable --now` 를 부른다. 유닛 파일은 **손으로 만들어** `--status` 만 재라
- **`QB_DISK_NOTIFY_CMD` 없이 비-dry-run 을 돌리지 마라** — 진짜 텔레그램 발송 경로다
- `awk`·`sed`·`grep` 스텁 금지. 스텁 대상은 `df`·`date`·`systemctl` 뿐이다
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- 앞 step 이 만든 테스트를 지우거나 이름을 바꾸지 마라 — AC 수집 하한이 누적값(≥10)이다
