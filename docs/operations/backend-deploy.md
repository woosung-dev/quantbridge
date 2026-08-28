# QuantBridge — BE·소크 스택 배포·롤백 런북

> **대상:** `truewords-oracle`의 `~/quantbridge`에서 도는 소크 6서비스와 호스트
> `quantbridge-api.service`. 서버 실측은 CONTROL의 책임이며, 이 문서는 레포 코드·스크립트로
> 확인한 사실만 쓴다.
> **정본:** 이 문서 + `tools/scripts/soak-stack.sh` +
> `tools/scripts/db-backup.sh` + `infra/compose/docker-compose{,.isolated,.soak}.yml`.
> **첫 도입:** [BL-777]. 기존 BE·소크 표기는 `pin`을 빠뜨린 채 `up`/`down`/`migrate`만 적었다
> (`docs/development/ci-cd.md:276-281`).

## 0. 어느 명령이 소크 창을 끊는가

| 명령                            | 창을 끊나                   | 근거                                                                                                                                                                                                                                                          |
| ------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `soak-stack.sh pin`             | **끊는다**                  | `pin`은 귀속을 흐리는 시점이라 창을 닫는다는 정의가 `tools/scripts/soak-stack.sh:45-47`에 있다. 실행 중 고정본 위 재-pin도 거부한다(`:187-197`).                                                                                                              |
| `soak-stack.sh down`            | **끊는다**                  | 같은 창 경계 정의(`tools/scripts/soak-stack.sh:45-50`)와 compose 중지 뒤 `down` 이벤트 기록(`:301-307`)이다.                                                                                                                                                  |
| `soak-stack.sh up`              | 연다                        | celery ready 시각으로 `up` 이벤트를 기록해 새 창을 연다(`tools/scripts/soak-stack.sh:275-299`).                                                                                                                                                               |
| `soak-stack.sh migrate`         | 안 끊는다                   | 컨테이너 생명주기를 바꾸지 않고 현재 DB에 `docker exec`만 한다(`tools/scripts/soak-stack.sh:324-407`). DDL 위험과 창 단절은 별개다. ★**그래서 `quantbridge-db` 가 떠 있어야 한다** — `down` 뒤에 부르면 전제 미충족으로 죽는다(§3.3).                                                                                                                           |
| `db-backup.sh run`              | 안 끊는다                   | 백업은 `docker exec`와 `docker cp`만 쓰며 기동·정지·재시작을 금지한다(`tools/scripts/db-backup.sh:50-62`, `:243-251`).                                                                                                                                        |
| FE `docker compose up -d`       | 안 끊는다                   | FE는 서비스·볼륨이 소크와 겹치지 않으며, 창을 끊는 것은 `pin`/`down`뿐이다(`infra/compose/docker-compose.frontend.yml:1-7`).                                                                                                                                  |
| `mise run up/down/migrate/seed` | **소크 배포에 쓰지 않는다** | 네 명령은 `assert-main-checkout`만 호출한다(`mise.toml:93-108`, `:240-245`, `:386-397`). 고정 소크를 막는 `assert-not-pinned`는 `up-isolated*` 세 갈래뿐이다(`mise.toml:166`, `:177`, `:189`). 즉 네 명령 전체가 고정본 보호로 막힌다는 해석은 코드와 다르다. |

`pin`만 해서는 새 코드가 실행되지 않는다. 프로세스는 이전 모듈을 import한 상태이므로
새 스냅샷을 반영하는 행위는 `up`이다(`tools/scripts/soak-stack.sh:187-195`, `:233-238`).

---

## 1. 이 배포가 무엇인가 (그리고 무엇이 아닌가)

**맞다** — main 체크아웃의 특정 커밋을 `.soak/src`에 고정하고, DB 스키마와 네 Celery 워커,
호스트 API를 명시 순서로 전환하는 운영 절차다. 소크 compose는 `db`, `redis`,
`backend-worker`, `backend-ws-stream`, `backend-optimizer-heavy`, `backend-beat`의 **6서비스**다.
`soak-gate.sh:43-47`은 optimizer-heavy를 빠뜨려 5종이라고 적지만, compose 코드가 정본이다
(`infra/compose/docker-compose.yml:93-220`).

**아니다** — 이미지 빌드·레지스트리 배포·자동 CD 런북이 아니다. 네 BE 서비스는 모두 `build:`만
있고 `image:` 태그가 없다(`infra/compose/docker-compose.yml:93-96`, `:127-130`, `:157-160`,
`:192-195`). 이 런북은 `apps/api/src`만 고정하는 소크 롤백을 다루며, 의존성 이미지의 버전
보관·재빌드·배포 경로는 레포에 없다.

**서버를 확인했다는 뜻도 아니다.** 아래의 호스트명·체크아웃·systemd 유닛·백업 파일은 모두
CONTROL이 §4와 `<보고>`의 명령으로 실제 상태를 확인해야 한다.

---

## 2. 구조 — 왜 이 모양인가

```text
서버 main 체크아웃 ── pin <sha> ──→ .soak/src (git archive)
                                      │ read-only bind mount
                                      ├─ backend-worker
DB + Redis ──────────────────────────├─ backend-ws-stream
                                      ├─ backend-optimizer-heavy
                                      └─ backend-beat

호스트 systemd: quantbridge-api.service ──→ 호스트 uvicorn
                                                (소크 compose의 서비스 아님)
```

**⑴ `pin`이 실질적인 코드 배포 단계다.** `_pin`은 다음 순서를 실제로 집행한다.

1. `assert-main-checkout.sh`로 워크트리를 거부한다(`tools/scripts/soak-stack.sh:182-186`,
   실패는 exit 2).
2. 실행 중인 고정본에 재-pin하는 것을 거부하며, `QB_SOAK_OVERRIDE=1`만 우회한다(`:187-197`).
3. `apps/api/src`의 dirty 상태를 거부한다(`:199-207`).
4. `_assert_no_missing_commits <sha>`가 `git fetch origin main`을 시도한 뒤,
   `<sha>..origin/main`을 `apps/api/src apps/api/scripts tools/scripts apps/api/alembic`으로
   필터한다(`:111-137`, `:148-177`, `:215-217`). fetch 실패는 “0개”가 아니라 “측정 못 함”이지만
   이 운영자 가드는 pin을 막지 않는다(`:151-161`).
5. `git archive <sha> apps/api/src`를 `.soak/src`에 풀고(`:219-226`),
   `tasks/celery_app.py`의 존재를 단언한다(`:228`).
6. stamp와 `.soak/pin-history.jsonl`에 `pin` 이벤트를 기록한다(`:230-238`).

소크층은 네 워커의 `/app/src`를 `./.soak/src:/app/src:ro`로 덮는다
(`infra/compose/docker-compose.soak.yml:32-97`). 따라서 소스 코드는 이미지에 구워진 실행물이
아니며, `down → pin <sha> → up`이 가능한 이유다.

**⑵ DDL은 명시적 축이며, 실제 DDL은 `down` 뒤 `up` 앞에 둔다.** `migrate`는 기본 dry-run이고
`--confirm`일 때만 `upgrade head`를 실행한다(`tools/scripts/soak-stack.sh:324-407`). `up`에
붙이면 창 중 DDL이 암묵적으로 실행되어 “무엇이 언제 스키마를 바꿨나”에 답할 수 없으므로 분리했다
(`:320-323`). 따라서 §3.3은 dry-run을 먼저 읽고, 승인 뒤 `down → migrate --confirm →
pin → up`을 둔다.

**⑶ API는 소크 compose 밖이다.** 소크 compose에는 API 역할이 없고 Celery의 `command:` override가
entrypoint의 migration 경로를 우회한다(`tools/scripts/soak-stack.sh:310-318`). 그래서 API 유닛
재시작이 별도 단계다(`docs/operations/better-auth-setup.md:113-121`).
~~`quantbridge-api.service`의 설치 파일·생성 스크립트는 레포에 없다.~~ → **2026-08-18 [BL-805]
해소**: `tools/scripts/api-service.sh --install`이 이 유닛을 만든다(형제 5종과 같은 heredoc 방식).
`--status`는 `ExecStart`의 uvicorn 절대경로를 현재 트리와 대조해 재배치를 잡는다. 다만 **서버에
실제로 설치된 유닛이 그 산출물과 같은지**는 여전히 CONTROL의 서버 read-back 대상이다 — 레포에
원본이 생긴 것과 서버가 그것으로 다시 구워진 것은 다른 사건이다.

**⑷ compose 프로젝트명은 경로에 묶인다.** 소크의 compose 인자에는 `-p`가 없고
`--project-directory "$ROOT"`만 있다(`tools/scripts/soak-stack.sh:30-41`). 따라서 Docker Compose의
기본 프로젝트명은 체크아웃 디렉터리 basename에 따른다. [가정] 서버가 `~/quantbridge`이면
`quantbridge`, 맥의 체크아웃이 `…/quant-bridge`이면 `quant-bridge`가 되어 네트워크·볼륨이 갈린다.
반면 FE compose는 외부 네트워크 이름을 `quantbridge_quantbridge`로 하드코딩한다
(`infra/compose/docker-compose.frontend.yml:62-67`). 서버의 실제 프로젝트명과 네트워크는 §4에서
확인해야 한다.

---

## 3. 배포 절차

### 3.1 최초 1회 (서버 준비)

1. CONTROL은 `truewords-oracle`에서 `~/quantbridge`가 main 체크아웃인지, Docker 데몬과
   `systemctl --user`가 살아 있는지 확인한다. `soak-stack.sh up`은 macOS에서 exit 2로 거부하므로
   소크 정본은 리눅스 서버다(`tools/scripts/soak-stack.sh:243-249`).
2. `quantbridge-api.service`의 유닛 파일, `WorkingDirectory`, `ExecStart`,
   `PROMETHEUS_MULTIPROC_DIR`를 확인한다. 유닛이 재배치 전 절대경로를 물면 죽은 경로로 남는다.
   이 위험과 점검 대상은 `docs/development/traps-environment-shell.md` §환경(mise 면제·워크스페이스 아님·격리 포트 항목)에 기록돼 있다.
   ~~**레포는 이 API 유닛을 만들지 않는다.**~~ → **2026-08-18 [BL-805]**: 이제 만든다
   (`tools/scripts/api-service.sh`). 아래 실측값이 그 인스톨러의 기준선이다. ★**2026-08-18 서버 실측 — 유닛은 실재하고 running 이다:**

   ```
   FragmentPath      = /home/ubuntu/.config/systemd/user/quantbridge-api.service
   ExecStart         = /home/ubuntu/quantbridge/apps/api/.venv/bin/uvicorn
                       src.main:app --no-server-header --host 127.0.0.1 --port 8100
   WorkingDirectory  = /home/ubuntu/quantbridge/apps/api
   Environment       = PROMETHEUS_MULTIPROC_DIR=/home/ubuntu/quantbridge/apps/api/.metrics
                       QB_METRICS_ROLE=api
   ```

   ★`ExecStart` 가 **`.venv` 절대경로**라 `uv sync` 로 venv 를 지웠다 다시 만들면 경로는 같지만
   **의존성은 그 시점 것**이다. 그리고 이 유닛만 레포에 생성 경로가 **0건**이라 서버를 갈아엎으면
   손으로 복원해야 한다 → [BL-805].

3. DB 백업 timer를 설치할 경우에만 `tools/scripts/db-backup.sh --install`을 실행한다. 이 스크립트가
   `~/.config/systemd/user/`에 heredoc 유닛을 만들며 `ExecStart`에 설치 시점 절대경로를 굽는다
   (`tools/scripts/db-backup.sh:461-533`). 경로 이동 뒤에는 반드시 `--status`로 신선도를 확인하고
   필요하면 `--install`을 다시 한다(`:545-581`).
4. user systemd timer/service가 SSH 종료 뒤에도 살아야 하면 `loginctl enable-linger` 상태를 확인한다
   (`docs/operations/frontend-deploy.md:163-165`).
   ★**2026-08-18 서버 실측 — `Linger=yes`** (`loginctl show-user ubuntu -p Linger`). 이미 켜져 있다.

### 3.2 서버 환경

`migrate --confirm`은 `apps/api/.env.local`을 **통째로** source해 advisory-lock 래퍼를 실행한다
(`tools/scripts/soak-stack.sh:387-395`). `DATABASE_URL`만 주입하거나 다른 DB URL을 임시로 넣지 마라.
스크립트는 publish된 DB 포트와 그 URL을 사전 대조하고(`:366-378`), 적용 후에는 컨테이너 안
`alembic_version`을 다시 읽는다(`:399-406`).

백업 설정은 설치 시점의 `QB_BACKUP_DIR`, `QB_BACKUP_BUCKET`, `QB_BACKUP_PREFIX`가 systemd 유닛에
굽힌다(`tools/scripts/db-backup.sh:476-485`). 현재 레포 주석이 가리키는 오프서버 위치는
`QB_BACKUP_BUCKET=truewords-backups QB_BACKUP_PREFIX=quantbridge`이며, 객체는
`quantbridge/quantbridge-<UTC timestamp>.dump`와 같은 prefix 아래에 있다
(`tools/scripts/db-backup.sh:26-35`, `:318-330`).

★**2026-08-18 서버 실측** — `QB_BACKUP_*` 는 `apps/api/.env.local` 에 **한 줄도 없다.** 즉 기본값이
그대로 쓰이고 로컬 덤프는 `/opt/backups` 다(실측 **보관 11개 / 664M**, 최근
`quantbridge-20260817T210028Z.dump` · `.meta` 의 `tables_min=tables_max=24`,
`ohlcv_rows=12,937`, `chunks=59`). 타이머는 `active waiting`, 설치본 신선도 ✓ 다.
**[확인 필요] 남는 것은 OCI 버킷 권한과 원격 객체 다운로드 경로 하나뿐**이다 — `--status` 는
로컬만 보여 준다.

`.env`의 값은 `KEY=value  # 주석` 형태일 수 있다. `cut -d= -f2`로 복사하면 주석이 값에 섞인다.
값을 옮겨야 한다면 주석을 제거하고 ASCII 여부를 검증한다
(`docs/operations/frontend-deploy.md:158-161`). 백업 자격증명·DB 대상의 판별은 `.env`가
아니라 실행 중 컨테이너에서 읽는다. 파일은 선언이고 컨테이너가 기동 시점의 실측이다
(`tools/scripts/db-backup.sh:54-62`).

### 3.3 매 배포 (서버에서 — 단일 복붙 블록)

아래 블록은 첫 실행에서 dry-run까지만 하고 안전하게 exit 2한다. **서버 소크 DB DDL의 명시 승인을
받은 뒤에만** `QB_DDL_APPROVED=NO`를 `YES`로 바꿔 처음부터 다시 실행한다. 이 승인 변수는
스크립트의 환경 변수가 아니라, 문서가 실수로 `--confirm`을 실행하지 않도록 둔 셸 가드다.

★**2026-08-28 실측으로 세 곳이 고쳐졌다** — 종전 블록은 405 커밋 점프 배포에서 두 번 걸렸다.
⑴ 미추적 파일을 세어 영원히 exit 2 · ⑵ `down` 뒤 `migrate` 는 **실행 불가능** · ⑶ `uv sync` 부재.

```bash
ssh truewords-oracle 'bash -lc '"'"'
set -euo pipefail
QB_DDL_APPROVED=NO  # 명시 승인 뒤에만 YES로 바꾼다.
cd ~/quantbridge

test "$(git branch --show-current)" = main
# ★`-uno` 다. 가드의 취지는 **추적 변경**인데 서버에는 배포와 무관한 미추적 백업
#   (`.env.bak-*` · 재배치 전 `backend/`)이 상시 있다. 그것을 세면 이 블록은 영원히 exit 2 다.
#   미추적이 pull 을 막는 경우는 main 에 같은 경로가 실재할 때뿐이니 그것만 따로 확인해라.
test -z "$(git status --porcelain -uno)" || {
  echo "✗ 추적 변경이 있는 체크아웃에는 배포하지 않는다" >&2
  exit 2
}
git pull --ff-only origin main
SHA="$(git rev-parse HEAD)"

# ① 의존성 동기화. ★소크는 `apps/api/src` 만 remount 하고 **venv 는 안 건드린다.**
#   호스트 API 의 ExecStart 는 `apps/api/.venv/bin/uvicorn` 이라 새 런타임 의존성이 붙으면
#   재시작이 곧 장애다 — 2026-08-28 실측: `openai>=1.60` 이 추가됐고 `src.main` 이
#   `strategy.router → service → narrative.service → narrative.providers` 로 그 체인을 문다.
#   Celery 워커 4대는 이미지에 굽힌 것을 쓰고 task 18개 중 이 체인을 무는 것은 0개다.
(cd apps/api && uv sync)
# ★재시작 **전에** import 를 재라. 살아 있는 API 를 죽이고 나서 알면 늦다.
#   `src` 는 설치 패키지가 아니라 CWD 의존이라 `PYTHONPATH=.` 가 필요하다(§8 BE AGENTS).
(cd apps/api && set -a && . ./.env.local && set +a \
  && PYTHONPATH=. .venv/bin/python -c "import src.main; src.main.create_app()")

# ② 대상 DB·현재 revision·적용 대기만 읽는다. DDL 없음.
tools/scripts/soak-stack.sh migrate
if [ "$QB_DDL_APPROVED" != YES ]; then
  echo "■ dry-run 완료. 서버 소크 DB DDL의 명시 승인 뒤 YES로 재실행" >&2
  exit 2
fi

# ③ 창을 닫고 → 고정본을 바꾸고 → **db 만 먼저 올려** DDL 을 넣고 → 전체를 연다.
#   ★★`down` 은 `quantbridge-db` 를 **제거**한다. 그래서 종전 문서의
#     `down → migrate --confirm` 순서는 실행할 수 없었다 — `migrate` 는 그 컨테이너에
#     `docker exec` 하므로 "alembic_version 을 못 읽었다 — 전제 미충족" 으로 죽는다.
#     DDL 을 워커 정지 중에 넣는다는 **의도**(§2 ⑵)는 db 만 올리는 것으로 그대로 지켜진다.
tools/scripts/soak-stack.sh down
tools/scripts/soak-stack.sh pin "$SHA"
docker compose --project-directory "$PWD" \
  -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.isolated.yml \
  -f infra/compose/docker-compose.soak.yml up -d db
until [ "$(docker inspect -f "{{.State.Health.Status}}" quantbridge-db)" = healthy ]; do sleep 2; done
tools/scripts/soak-stack.sh migrate --confirm
tools/scripts/soak-stack.sh up

# ④ 소크 compose 밖의 호스트 API를 반영한다.
systemctl --user restart quantbridge-api.service
sleep 10

# ⑤ 게이트가 읽는 실행 상태를 순서대로 되읽는다.
#   ★헬스는 `/health` 로 재라. `/healthz` 는 12초 상한이 12.89초 celery inspect 를 감싸
#     구조적으로 200 이 안 나온다(`frontend-deploy.md` §5) — 503 은 배포 실패가 아니다.
curl -s --max-time 10 http://127.0.0.1:8100/health; echo
tools/scripts/soak-stack.sh commit
tools/scripts/soak-stack.sh status
tools/scripts/soak-gate.sh
'"'"''
```

★**게이트는 배포 직후 exit 2(UNKNOWN)가 정상이다** — `up` 이 새 창을 열었으므로 연속 시간이
0 에서 다시 센다. 직전 창의 누적은 구 SHA 로 닫힌다. 이것은 배포의 비용이지 결함이 아니다.

`soak-stack.sh`에는 `ssh`가 0건이다. 운영자가 위처럼 `ssh truewords-oracle 'bash -lc …'`로 감싸야
하며, `bash -lc`는 비로그인 셸에서 `uv` PATH가 빠지는 것을 막는다
(`docs/operations/frontend-deploy.md:112-131`).

### 3.4 롤백

#### ⑴ 소크 워커 코드 롤백

```bash
# 서버에서, 현재 main 체크아웃을 유지한 채 이전 고정본으로만 되돌린다.
tools/scripts/soak-stack.sh down
QB_SOAK_OVERRIDE=1 tools/scripts/soak-stack.sh pin <이전-sha>
tools/scripts/soak-stack.sh up
tools/scripts/soak-stack.sh commit
tools/scripts/soak-gate.sh
```

이것은 `.soak/src:/app/src:ro` bind mount를 쓰므로 가능한 소스 롤백이다
(`infra/compose/docker-compose.soak.yml:32-97`). 대가는 **연속 소크 창 단절**이다. 이전 SHA 뒤에는
대개 감시 경로 커밋이 남으므로 `_assert_no_missing_commits`가 pin을 거부한다. 그 거부를 이해한
롤백에만 `QB_SOAK_OVERRIDE=1`을 붙인다(`tools/scripts/soak-stack.sh:148-177`). 후보 SHA와 pin 시각은
`.soak/pin-history.jsonl`에 남는다(`:32-35`, `:230-231`).

이 절은 **네 소크 워커의 `apps/api/src`만** 되돌린다. 호스트
`quantbridge-api.service`가 어느 checkout·venv를 실행하는지는 `api-service.sh --status`로 **읽을 수
있게 됐지만**([BL-805], 2026-08-18), API까지 같은 SHA로 되돌리는 절차는 여전히 [확인 필요]다 —
유닛은 checkout을 가리킬 뿐이고 그 checkout을 옛 SHA로 옮기는 것은 이 문서의 범위 밖이다. 확인 없이 API 유닛을 restart하면 현재 checkout의
코드를 다시 읽을 수 있다.

#### ⑵ 의존성이 바뀐 커밋의 한계

`pyproject.toml`이나 `uv.lock`을 넘는 롤백은 이 경로로 할 수 없다. `pin`은 `apps/api/src`만
archive하고(`tools/scripts/soak-stack.sh:219-226`), 네 서비스는 `build:`만 선언하며 sha 태그·레지스트리
참조가 없다(`infra/compose/docker-compose.yml:93-96`, `:127-130`, `:157-160`, `:192-195`).
즉 필요한 이전 이미지를 식별·재빌드·보관·배포하는 경로는 스크립트와 문서 어디에도 없다.
**이 한계의 해결책은 현재 레포가 모른다.**

#### ⑶ DB 롤백 — 백업 복원

`db-backup.sh verify-restore`는 앱 DB로 되돌리는 명령이 아니다. `qb_restore_verify_*` throwaway
DB만 만들고 `trap`에서 `DROP DATABASE`한다(`tools/scripts/db-backup.sh:343-370`, `:409-459`).
앱 DB 복원 명령은 스크립트에도 기존 런북에도 없다.

아래는 그 공백을 드러낸 **[확인 필요] 제안 절차**다. CONTROL은 첫 실제 복원 전에 별도 승인과
복원 리허설을 받아야 하며, 이 문서는 이를 실행·검증하지 않았다.

```bash
# [확인 필요] 앱 DB 복원 — 모든 쓰기자를 먼저 멈춘 뒤에만, 명시 승인 하에 실행한다.
set -euo pipefail
cd ~/quantbridge
DUMP=/opt/backups/quantbridge-<UTC timestamp>.dump
test -s "$DUMP"
test -f "$DUMP.meta"

systemctl --user stop quantbridge-api.service
tools/scripts/soak-stack.sh down
docker cp "$DUMP" quantbridge-db:/tmp/qb-app-restore.dump
docker exec quantbridge-db psql -U quantbridge -d postgres -v ON_ERROR_STOP=1 \
  -c 'DROP DATABASE quantbridge WITH (FORCE);' \
  -c 'CREATE DATABASE quantbridge;'
docker exec quantbridge-db psql -U quantbridge -d quantbridge -v ON_ERROR_STOP=1 \
  -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;' \
  -c 'SELECT timescaledb_pre_restore();'
docker exec quantbridge-db pg_restore --no-owner --no-acl --clean --if-exists \
  -U quantbridge -d quantbridge /tmp/qb-app-restore.dump
docker exec quantbridge-db psql -U quantbridge -d quantbridge -v ON_ERROR_STOP=1 \
  -c 'SELECT timescaledb_post_restore();' \
  -c 'SELECT version_num FROM alembic_version;'
docker exec quantbridge-db rm -f /tmp/qb-app-restore.dump
# 복원 revision과 되돌릴 코드 SHA의 호환성을 확인한 뒤에만 pin → up → API start 한다.
```

`timescaledb_pre_restore()`/`post_restore()`는 현재 스크립트에도 남아 있지만, 2026-08-16 실측에서
호출 유무의 관측 차이는 0개였다. 현재 스키마에서는 [가정] 호출할 고유 기능이 없었을 수 있으며,
짝 하네스도 두 호출을 지워도 39/39 초록이라 판별력이 없다
(`tools/scripts/db-backup.sh:348-358`). 따라서 `:433-441`의 “없으면 복원이 깨진다”는 die 문구를
보호 증거로 읽지 마라.

오프서버 사본은 `truewords-backups` 버킷의 `quantbridge/` prefix부터 찾는다
(`tools/scripts/db-backup.sh:29-33`, `:318-330`). [확인 필요] OCI에서 원본 덤프와 `.meta`를
가져오는 명령·권한은 레포에 없다. 이 스크립트에는 업로드만 있고 특정 기존 덤프를 재업로드하는
서브커맨드도 없다.

#### ⑷ DB 롤백 — Alembic downgrade

`downgrade`도 서버 소크 DB DDL이므로 **매번 명시 승인 대상**이다. 상태 정본은 “migration 파일 생성과
로컬/CI 적용은 허용, 서버 소크 DB DDL 적용은 매번 명시 승인”이라고 구분한다
(`docs/status.md:41-53`). `soak-stack.sh`에는 `migrate --downgrade`가 없고 dispatch도 여덟
서브커맨드만 제공한다(`tools/scripts/soak-stack.sh:541-552`).

수동 CLI는 `_test` 접미가 아닌 DB의 downgrade만 막으며, 탈출구는 환경 변수가 아니라
`-x allow_destructive=1`이다. `.env.example`에 없는 환경 변수를 코드가 참조하지 않는 규칙을
지키기 위해서다(`apps/api/alembic/env.py:55-73`, `:106-125`). 그러므로 명시 승인·백업·대상 DB
read-back 뒤에만 다음의 **[확인 필요] 서버 절차**를 사용한다.

```bash
# [확인 필요] 실행 전: 백업 파일 + .meta, 현재 revision, 목표 revision, DDL 명시 승인을 대조한다.
cd ~/quantbridge/apps/api
set -a; . ./.env.local; set +a
uv run alembic current
uv run alembic -x allow_destructive=1 downgrade <목표-revision>
uv run alembic current
```

---

## 4. 검증 (순서 있음)

아래는 §3.3 성공 뒤 CONTROL이 서버에서 순서대로 읽을 명령이다. 새 창 직후 `soak-gate.sh`의
PASS는 기대값이 아니다. PASS만 exit 0이고, 아직 24시간 창을 못 채운 결과는 FAIL 또는 UNKNOWN일 수
있다(`tools/scripts/soak-gate.sh:15-17`).

```bash
# 1. 각 서비스가 새 고정본 mount를 볼 준비인가
cd ~/quantbridge
docker compose --project-directory . \
  -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.isolated.yml \
  -f infra/compose/docker-compose.soak.yml ps
# 기대: db, redis, backend-worker, backend-ws-stream, backend-optimizer-heavy,
#       backend-beat가 running. API 컨테이너는 없어야 정상이다.

tools/scripts/soak-stack.sh commit
# 기대: celery MainProcess가 보는 /app/src/__soak_commit__ SHA = 배포 SHA.

tools/scripts/soak-stack.sh status
# 기대: /app/src ← .soak/src, 고정 SHA, 활성 세션 수. “누락 커밋: 측정 못 함”은 최신이라는 뜻이 아니다.

systemctl --user status --no-pager quantbridge-api.service
# 기대: active (running). 유닛 부재·삭제된 WorkingDirectory·rc=203/EXEC면 중단한다.

curl -fsS http://127.0.0.1:8100/health
# 기대: 200과 health JSON. 재시작 직후에는 최대 약 8초 기다린다
#       (docs/operations/frontend-deploy.md:163-168).

tools/scripts/soak-gate.sh
# 기대: 표본을 남기고 PASS/FAIL/UNKNOWN 중 하나를 명시한다. 새 창은 PASS가 아니라는 사실을 기록한다.
```

게이트는 현재 기본으로 `apps/api/.metrics`를 직독하므로 API 컨테이너가 없어도 C5를 판정한다
(`tools/scripts/soak-gate.sh:43-49`). 다만 이 스크립트는 고정본이 아니라 서버 체크아웃에서 실행되므로,
서버 체크아웃을 먼저 갱신하지 않으면 판정기 자체가 낡을 수 있다
(`docs/operations/frontend-deploy.md:140-143`).

---

## 5. 함정 (전부 실측으로 물린 것)

★**`soak-stack.sh`는 SSH를 하지 않는다.** 스크립트 안 `ssh` 검색은 0건이다. 운영자가
`ssh truewords-oracle 'bash -lc "cd ~/quantbridge && …"'`로 감싸고, login shell의 PATH로 `uv`를
확보해야 한다. `up`은 macOS에서 exit 2로 거부한다(`tools/scripts/soak-stack.sh:243-246`).

★**`--project-directory` 경고를 이 경로에 복붙하지 마라.** 소크 스크립트가 이미
`--project-directory "$ROOT"`를 compose 배열에 넣는다(`tools/scripts/soak-stack.sh:30-41`).
FE 배포의 `--project-directory` 누락 경고(`docs/operations/frontend-deploy.md:95-98`)와
`ci-cd.md`의 경고(`docs/development/ci-cd.md:283-284`)는 이 wrapper 경로에는 해당하지 않는다.

★**프로젝트명·네트워크를 파일명처럼 가정하지 마라.** `-p`가 없는 소크 compose의 프로젝트명은
checkout basename에서 파생한다. [가정] `~/quantbridge`와 `…/quant-bridge`는 서로 다른 프로젝트명이므로
네트워크·볼륨도 갈린다. FE는 `quantbridge_quantbridge`를 하드코딩한다
(`infra/compose/docker-compose.frontend.yml:62-67`). **진짜 판별자**는 서버의
`docker compose … config --services`와 `docker network ls` 출력이다.

★**“소크가 5서비스”는 조용히 틀린다.** `soak-gate.sh:43-47`의 주석은 optimizer-heavy를 빼고
5종이라 하지만 compose에는 네 backend 서비스와 DB·Redis가 있다
(`infra/compose/docker-compose.yml:93-220`). **진짜 판별자**는 §4의 3층 compose `ps`다.

★**백업 rc=3은 “백업 없음”이 아니다.** 로컬 덤프가 정상이고 원격 업로드만 실패한 부분 성공이며,
systemd는 이를 실패로 보고 Telegram `OnFailure`를 발화한다(`tools/scripts/db-backup.sh:39-43`,
`:295-315`, `:471-505`). 알람을 받으면 ① journal에서 rc=3을 확인하고 ② 로컬 `.dump`와 `.meta`를
`verify-restore`로 throwaway DB에 검증하고 ③ OCI CLI·버킷·prefix를 확인한다. **진짜 판별자**는
원격 객체와 로컬 복원 실증 둘 다다. 원본을 재업로드하는 서브커맨드는 없으며, `run`은 새 덤프를
만들어 다시 업로드할 뿐이다.

★**systemd 유닛 파일은 레포에 영속되어 있지 않다.** `db-backup.sh --install`은 heredoc으로
`~/.config/systemd/user/`에 쓰고 절대 `ExecStart`를 굽는다(`tools/scripts/db-backup.sh:461-533`).
그래서 재배치 뒤 “timer waiting”은 통과처럼 보이지만 실제는 rc=127일 수 있다. **진짜 판별자**는
`db-backup.sh --status`의 `ExecStart` 신선도다(`:545-581`).
`quantbridge-api.service`는 이 스크립트(`db-backup.sh`)가 만들지 않는다. ~~레포에 설치 경로도
없다~~ → **2026-08-18 [BL-805]**: 전용 인스톨러 `tools/scripts/api-service.sh`가 생겼다. 신선도
**진짜 판별자**는 `api-service.sh --status`의 `ExecStart` uvicorn 경로 대조다(형제들은
`ExecStart=/bin/bash <스크립트>`를 파싱하지만 이쪽은 `.venv/bin/uvicorn`이라 파서가 다르다).
★**2026-08-19 적대 리뷰로 축이 넷이 됐다** — ⑴ 경로 ⑵ **wrapper의 shebang이 가리키는 인터프리터
실재**(venv는 재배치 불가라 checkout을 복사하면 파일은 따라오는데 첫 줄은 삭제된 옛 venv를 가리켜
`203/EXEC`로 죽는다 — `[ -x ]`로는 못 본다) ⑶ **drop-in 합성**(`<unit>.d/*.conf`가 `ExecStart`를
재지정하면 원본 파일은 최신인데 도는 것은 옛 checkout이라, 파일 축과 `systemctl show` 축을 둘 다
본다) ⑷ **활성 상태**(`is-failed`/`is-active` — 앞 셋이 전부 초록이어도 기동 직후 죽으면 `failed`다).
판정 불가(바이너리·`env` 경유 shebang·미확장 `${VAR}`)는 조용히 통과시키지 않고 그 사실을 인쇄한다.
restart 지시는 `better-auth-setup.md`에 있고(`docs/operations/better-auth-setup.md:117-120`);
서버에 실제로 도는 유닛은 §4에서 읽어야 한다.

★**`.env` 값 추출과 실행 중 자격증명을 혼동하지 마라.** 인라인 주석을 값에 섞으면 401이 아니라
500이 될 수 있다(`docs/operations/frontend-deploy.md:158-161`). 또 `.env`는 편집 뒤에도
컨테이너가 쥔 값을 말해주지 않는다. **진짜 판별자**는 컨테이너에서 읽은 DB 사용자·DB 이름·published
port다(`tools/scripts/db-backup.sh:54-62`, `:201`).

---

## 6. 관련 문서

- 소크 게이트·유닛 함정: [gates-and-traps.md](../development/gates-and-traps.md) · [ADR-024](../adr/024-soak-stability-gate.md)
- DB 보관 책임: [ADR-033](../adr/033-db-hosting-self-host-timescaledb.md) · 인증 배포 보완: [better-auth-setup.md](./better-auth-setup.md)
- FE와 분리된 배포: [frontend-deploy.md](./frontend-deploy.md) · 기존 CD 표기: [ci-cd.md](../development/ci-cd.md)
- 서버 소크 DB DDL 승인 경계: [status.md](../status.md)
