# QuantBridge — FE 오라클 배포 런북

> **대상:** `qb.woosung.dev`(FE) · `qb-api.woosung.dev`(API) — 오라클 Always Free A1(도쿄, aarch64).
> **정본:** 이 문서 + `docker-compose.frontend.yml` + `apps/web/Dockerfile`.
> **첫 도입:** 2026-08-07 fe-oracle-deploy 회차. 소크([BL-003]) 창을 끊지 않고 올렸다.

---

## 1. 이 배포가 무엇인가 (그리고 무엇이 아닌가)

**맞다** — 브라우저에서 소크가 도는 실계정 화면을 본다. 앞단은 **Cloudflare Access(이메일 OTP)**다.

**아니다** — 공개 서비스가 아니다. `APP_ENV` 는 여전히 `development` 다.
★2026-08-17 [ADR-034] — 인증은 self-host Better Auth 로 바뀌었고 **이 FE 컨테이너가 인증 서버**다.
배포 절차에 alembic 적용 + 전용 DB 롤이 붙는다: [`better-auth-setup.md`](./better-auth-setup.md).
공개 전환은 [BL-071] 이 소유한다.

**소크에 아무것도 더하지 않는다** — 이 스택은 소크 compose 3층과 서비스도 네트워크도 공유하지
않는다. 올리고 내려도 C1/C2 는 그대로다.

---

## 2. 구조 — 왜 이 모양인가

```
브라우저 ─(Access OTP)─→ qb.woosung.dev  ─┐
브라우저 ─(세션 JWT)──→ qb-api.woosung.dev ─┤
                                            ├→ quantbridge-cloudflared (network_mode: host)
                                            │     ├→ 127.0.0.1:3200 → quantbridge-frontend
                                            │     └→ 127.0.0.1:8100 → 호스트 uvicorn
FE 컨테이너 ─(SSR 헤어핀)─→ qb-api.woosung.dev ┘
```

세 가지 결정에 각각 실측 근거가 있다.

**⑴ 빌드는 맥, 서버는 실행만.** 서버는 2 OCPU 를 다른 프로젝트와 공유하고 그 위에서 소크가 돈다.
서버 빌드는 소크 워커를 굶긴다. 서버에 Node 는 **설치돼 있지 않다** — 그래서 `next start` 가 아니라
`output: "standalone"` + `node:22-alpine` 이미지다. 맥(darwin/arm64)과 서버(aarch64)가 같은
아키텍처라 `--platform linux/arm64` 는 에뮬레이션 없이 네이티브다.

**⑵ 전용 터널이고 `network_mode: host` 다.** 서버에 이미 `cloudflared` 가 있지만 그건 다른
프로젝트의 것이고 **브리지 네트워크 안**에 있다. 호스트 iptables 는 `INPUT` 에서 22 만 ACCEPT 하고
나머지를 REJECT 하므로 **브리지→호스트 `127.0.0.1:8100` 경로가 구조적으로 없다**. host 네트워크로
띄우면 uvicorn 바인딩도 iptables 도 남의 프로젝트도 손대지 않는다.

**⑶ 호스트명 2개다.** `NEXT_PUBLIC_API_URL` 은 **빌드 타임 인라인**(`apps/web/src/lib/api-base.ts`)
이라 도메인을 정한 뒤에 빌드해야 한다. 단일 호스트 + Next rewrites 는 CORS 를 없애주지만
**WebSocket 을 안 넘긴다** — 이 앱은 `/realtime/ws` 를 쓴다.

★**`qb-api.woosung.dev` 에는 Access 를 걸지 마라.** Access 는 브라우저 리다이렉트로 인증하는데
XHR 도 FE 컨테이너의 SSR 헤어핀도 그 리다이렉트를 못 따라간다. API 의 문은 Bearer JWT 다.

---

## 3. 배포 절차

### 3.1 최초 1회 (Cloudflare 대시보드)

1. Zero Trust → Networks → Tunnels → **Create a tunnel** (`quantbridge`) → 토큰 복사
2. Public Hostname 2건 — `qb.woosung.dev` → `HTTP` `localhost:3200` ·
   `qb-api.woosung.dev` → `HTTP` `localhost:8100`
3. Zero Trust → Access → Applications → Self-hosted — 도메인 `qb.woosung.dev`, 정책 = 허용 이메일

### 3.2 최초 1회 (서버 env)

`~/quantbridge/apps/api/.env.local`:

```
FRONTEND_URL=https://qb.woosung.dev              # CORS(main.py) + WS origin 검사(realtime/router.py)
PROMETHEUS_BEARER_TOKEN=<openssl rand -hex 32>   # 공개 /metrics 차단
BETTER_AUTH_URL=https://qb.woosung.dev           # JWT iss/aud — FE와 반드시 동일
BETTER_AUTH_JWKS_URL=http://127.0.0.1:3200/api/auth/jwks  # API→FE 내부 JWKS
```

`~/quantbridge/.env`:

```
QB_FRONTEND_TAG=<맥에서 build 한 태그>
QB_TUNNEL_TOKEN=<3.1 의 토큰>
BETTER_AUTH_SECRET=<openssl rand -base64 32>
BETTER_AUTH_URL=https://qb.woosung.dev
BETTER_AUTH_DATABASE_URL=postgresql://<auth-role>:<password>@<db-host>:5432/<db-name>
```

`BETTER_AUTH_SECRET`·`BETTER_AUTH_URL`·`BETTER_AUTH_DATABASE_URL`은 frontend compose가
기동 전에 요구한다. API의 `BETTER_AUTH_URL`은 동일 공개 origin, `BETTER_AUTH_JWKS_URL`은
컨테이너 내부 FE 주소여야 터널 왕복 없이 JWT를 검증한다.

★`PROMETHEUS_BEARER_TOKEN` 은 `APP_ENV=production` 없이도 강제된다. **게이트가 `QB_METRICS_URL`
없이(= `.metrics` 직독) 도는지 먼저 확인해라** — HTTP 갈래는 베어러 헤더를 안 보내서 401 이 되고
C5⑷ 가 영구 ✗ 가 된다([BL-624]).

### 3.3 매 배포 (맥 → 서버)

```bash
QB=/Users/woosung/project/agy-project/quant-bridge
cd $QB/apps/web
# .env.production.local 에 NEXT_PUBLIC_* 4종 (gitignored). 도메인이 바뀌면 반드시 재빌드.
pnpm build
TAG=$(git rev-parse --short HEAD)
docker build --platform linux/arm64 -t quantbridge-frontend:$TAG .
docker save quantbridge-frontend:$TAG | gzip -1 | ssh <서버> 'gunzip | docker load'
ssh <서버> "sed -i 's/^QB_FRONTEND_TAG=.*/QB_FRONTEND_TAG=$TAG/' ~/quantbridge/.env"
# ★`--project-directory` 필수 — 없으면 compose 가 `.env` 를 **첫 -f 의 디렉터리**(infra/compose/)에서
#   찾아 `BETTER_AUTH_SECRET is missing` 으로 죽는다. [ADR-029] 재배치 이후 이 명령은 깨져 있었고
#   2026-08-16 배포에서 처음 밟았다(그전 배포는 재배치 이전이라 통과했다).
ssh <서버> 'cd ~/quantbridge && docker compose --project-directory /home/ubuntu/quantbridge -f infra/compose/docker-compose.frontend.yml -p quantbridge-fe up -d'

# ★배포 직후 회수 — **최신 3태그만 남긴다**(§3.4 롤백 창이 3세대). 빼먹으면 커밋마다
#   109MB 짜리 죽은 태그가 무한히 쌓인다(2026-08-30 실측: 4벌 중 3벌이 죽은 것 = 328MB).
#   ★`docker image prune` 을 쓰지 마라 — 이 호스트는 3개 프로젝트가 디스크 한 벌을 공유하고
#     무차별 prune 은 남의 롤백 태그를 지운다(`traps-environment-shell.md` §디스크).
#     태그를 지정한 `rmi` 와 기간을 건 `builder prune` 만이 그 금지 밖이다.
ssh <서버> 'docker images quantbridge-frontend --format "{{.ID}}" | tail -n +4 \
  | xargs -r docker rmi 2>/dev/null; docker builder prune -f --filter until=168h'
```

실측: standalone 50MB · 이미지 211MB · 빌드 약 1분.

### 3.4 롤백

이전 태그가 서버에 남아 있으면 `QB_FRONTEND_TAG` 만 되돌리고 `up -d`. 남아 있지 않으면 3.3 을
이전 커밋에서 다시 밟는다. **FE 롤백은 소크와 무관하다.**
★**보존은 3세대까지다**(§3.3 의 회수가 그 넷째부터 지운다). 더 옛 것으로 가려면 3.3 재실행이다.

---

## 4. 검증 (순서 있음)

```bash
# ★게이트가 최우선. 반드시 `bash -lc` 로 불러라 (아래 §5 첫 함정)
ssh <서버> 'bash -lc "cd ~/quantbridge && tools/scripts/soak-gate.sh"'   # 실격 0 · C5 전건 ✓
ssh <서버> 'curl -s -o /dev/null -w "%{http_code}\n" localhost:3200'          # 200
curl -s https://qb-api.woosung.dev/health                                     # {"status":"ok",...}
curl -s -o /dev/null -w "%{http_code}\n" https://qb-api.woosung.dev/metrics   # 401
# ★401 **하나로는 못 가른다** — 아래 §5 참조. 부팅 로그 1줄이 판별자다 ([BL-704]).
ssh <서버> 'docker logs <api 컨테이너> 2>&1 | grep -m1 metrics_auth='   # enabled 여야 한다
```

그다음 브라우저 — Access OTP → 로그인 → `/strategies` 렌더(SSR 헤어핀 정상) →
`/trading` 세션 진단 패널의 WS 상태 `authed`(CORS + WS origin 정상).

---

## 5. 함정 (전부 실측으로 물린 것)

★**게이트를 비로그인 ssh 셸에서 부르지 마라.** `ssh <서버> 'tools/scripts/soak-gate.sh'` 는 PATH 에
`uv` 가 없어 phantom 분류기가 실패하고, 그 창의 시간이 **커버리지에서 잘려나간다**(실측 8분).
`bash -lc` 로 감싸라. systemd 타이머는 `Environment=PATH=` 로 명시돼 있어 영향받지 않는다.

★★**`/metrics` 의 401 은 두 가지를 동시에 뜻한다 — 「보호 중」과 「관측 상실」.** 2026-08-11
fail-closed 전환 이후 토큰이 **없어도** 401 이다(있으면 베어러 없는 요청이 401, 없으면 전건 401).
즉 위 §4 의 `curl … # 401` 은 **판별자가 아니다.** 판별자는 부팅 로그 1줄이다 —
`metrics_auth=enabled app_env=…`(정상) / `metrics_auth=DISABLED …`(토큰 누락, 스크레이프 전멸).
★이 호스트는 `APP_ENV` 미설정이라 `core/config.py` 의 production validator 보호를 **안 받는다**.
그래서 그 줄은 `app_env` 조건 **없이** 모든 환경에서 찍힌다([BL-704]).

★**게이트 스크립트는 소크 고정본이 아니라 체크아웃에서 돈다.** 서버 체크아웃이 낡으면 게이트도
낡는다 — 2026-08-07 에 서버가 [BL-620] **이전** 커밋이라 HTTP 로 긁고 있었고, 그 상태에서
베어러 토큰을 켜자 C5 가 죽었다. 게이트 출력의 `darkness_computed=✓` 는 **어느 경로로 성공했는지
말해주지 않는다** — 판별자는 API 로그의 `GET /metrics` 유무다.

★**서버 클론이 `--single-branch`(main 전용)다.** feature 브랜치는 refspec 을 명시해야 온다:
`git fetch origin <branch>:refs/remotes/origin/<branch>`([BL-623]).

★**체크아웃 전환은 소크에 안전하다** — 워커는 `.soak/src`(미추적 스냅샷)와 `apps/api/.metrics` 만
마운트한다. `.env.local`·`.soak/session` 도 미추적이라 살아남는다. 단 **추적 파일 변경이 0건인지
먼저 확인**해라.

★★**서버 `apps/api/.env.local` 에 플레이스홀더 시크릿이 있어도 아무것도 안 잡는다.** 실측:
종전 `CLERK_SECRET_KEY=sk_test_...`(문자 그대로)인 채로 API 가 정상 기동하고 `/health` 는 200 을
낸다 — 인증 경로를 밟는 요청이 처음 들어올 때 **전건 401** 로 드러난다. 진짜 키는 루트 `.env`
에만 있었다. `APP_ENV=production` 이면 validator 가 기동 시점에 잡지만 development 는 통과시킨다.
⇒ **배포 검증은 반드시 로그인 후 데이터 화면까지** 가야 한다. `/health` 200 은 아무 증거가 아니다.

★★**`.env` 값에 인라인 주석이 붙는다** — 이 레포 관례가 `KEY=value    # [필수 …]` 다.
`cut -d= -f2` 로 값을 옮기면 주석의 **한글이 값에 섞여 들어간다.** 그러면 401 이 아니라 **500** 이
난다(구 clerk SDK 가 헤더를 ascii 로 인코딩 → `UnicodeEncodeError`). 값 추출은 항상
`split("#")[0].strip()` 하고 `isascii()` 로 단언해라.

★**API 기동은 8초 걸린다.** `systemctl --user restart` 직후 6초에 curl 하면 `000` 이 나온다.

★**systemd user service 는 lingering 없이 ssh 세션과 함께 죽는다** — `loginctl enable-linger`.

★**`/healthz` 는 구조적으로 200 이 안 나온다**(`asyncio.timeout(12.0)` 이 12.89초짜리 `inspect` 를
감싼다). 헬스 판정에는 `/health` 를 써라. 게이트는 둘 다 안 쓴다.

---

## 6. 관련 문서

- 소크 게이트 판정: [`gates-and-traps.md`](../development/gates-and-traps.md) · [ADR-024](../adr/024-soak-stability-gate.md)
- 환경 변수 정본: [`env-vars.md`](../development/env-vars.md) · 인증: [`better-auth-setup.md`](./better-auth-setup.md)
- 공개 전환(= `APP_ENV=production`): [BL-071] · 그때 되살릴 운영 절차: [BL-617]
