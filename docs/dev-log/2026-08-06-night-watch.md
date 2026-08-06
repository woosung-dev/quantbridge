# 2026-08-06 — night-watch: 밤샘 오케스트레이션으로 A~D 를 닫고 [ADR-025] 를 Accepted 로

**결과 한 줄** — opus 생성자 3 pane + codex 적대 리뷰 3회 + 리뷰 2축으로 [BL-594]·[BL-596]
Resolved / [BL-591] P1→P2 / **[ADR-025] Accepted**(12h 전향 예측 전건 충족) / 계획된 재기동
1회로 B2 실증. 밤 diff = `backend/src` **0줄** · FE **0줄**. 소크 실격 **0** 유지, 누적은
재기동을 넘어 **12.75h** 로 이어졌다.

## 반증된 전제 (성공보다 먼저)

1. **★「PR #544 OPEN · 미머지」는 착수 시점에 이미 거짓이었다** — 13:22:55Z 에 MERGED,
   main == origin/main. 지시문의 base(`stage/conditional-stop-ownership`)를 그대로 썼으면
   낡은 브랜치 위에서 밤을 보냈다. **착수 첫 실측이 base 를 main 으로 바꿨다**(§7.1 재확인).
2. **★★「격리 스택(6380)에서 B2 검증」은 성립하지 않는다** — `docker-compose.isolated.yml` 은
   redis 의 **포트만** override 한다. 같은 `container_name` · 같은 named volume
   (`quant-bridge_redis-data`, docker 실측 1개). 격리 redis = 소크 redis. ⇒ B2 는 예비 순서
   (A 판정 후 재기동 1회)로 확정했고, 기전 검증은 **스크래치 컨테이너**(별도 이름·임시 볼륨)로
   프로덕션 무접촉으로 했다.
3. **★★e2e authed 1건 red 는 알려진 hydration flake 가 아니었다** — 서명이 달랐다
   (`toContain` 단언 실패). 받은 문자열이 **소크 세션의 열린 포지션 표**였다: 라이브 포지션이
   열리면 페이지에 표가 하나 더 생기고 테스트의 느슨한 테이블 로케이터가 그 표를 집는다.
   단독 재실행 PASS · 2차 전체 실행 69 전건 PASS. **「소크 상태 ↔ e2e」 결합이라는 새 축** —
   [BL-597] 등재. 서명이 다른 red 를 기존 flake 로 접지 않은 것이 이 발견을 만들었다.
4. **★[BL-594] 백로그의 후보 원인 2종이 실측으로 반증됐다**(redis594 워커) — 「하드 kill 중
   쓰기」는 쓰기 한복판 SIGKILL 2회 모두 AOF 유효(diff=0), 기록된 손상은 파일 **13% 지점**이라
   꼬리 쓰기가 만들 수 없는 모양 ⇒ `stop_grace_period` · `appendfsync` **기각**. 유일 구속은
   `auto-aof-rewrite-min-size`(base 88바이트라 증가율 조건이 항상 참 → 크기만 구속)이고
   **rewrite 가 낡은 incr 을 지워 손상을 치유**한다(실측: 손상 incr 위에서 rewrite → 재기동 성공).
5. **★`redis-check-aof` 의 exit code 는 판별식이 못 된다** — 꼬리 절단은 exit 1 인데 서버는
   뜬다(`aof-load-truncated`). 반대로 페이로드 안 명령 이름을 깨면 `valid`(exit 0)인데 서버는
   죽는다 — **그 도구는 프레이밍만 본다**. 게이트는 양성 서명만 통과시키고(마지막 INCR 의
   short-read 만 허용), 페이로드 한계는 [BL-594] 잔여로 명기했다.
6. **Spec 리뷰어의 「report.md/status 부재」는 계약 오독(반증)** — 산출물은 fleet 계약대로
   **워크트리 쪽**에 실재했다. 단 그 안의 관측 하나는 실질이었다: gate596 이 남긴
   「`AUTOMATIC_DEATH_REASONS` 는 enum 정합 테스트가 있어 fail-open 이 아니다 — [BL-596] 의
   진짜 뿌리는 라벨의 정본이 enum 이 아니라 스크립트 안 문자열이라 대조 대상이 없던 것」이
   레포 문서에 없었다 → 본 회고에 수록(추가 방어는 분류기 동결 해제 시의 후보).
7. **내 실수 2건** — ⑴ Bash 호출 간 **cwd 가 지속**되는 걸 잊고 병합 중 `NNTESTS` 자리표시가
   커밋에 들어갔다(즉시 실측값 36 으로 amend). ⑵ 같은 함정으로 e2e 단독 재실행 한 번이
   엉뚱한 테스트를 돌렸다(재실행으로 정정). 「이미 그 디렉터리다」를 가정하지 말 것.

## 무엇을 했나

- **함대**: `herdr-fleet.sh` opus 3 pane(`redis594`/`adr023`/`gate596`, base `c6201490`) +
  `fleet-dispatch.sh`. pred pane 은 계획대로 미생성 — A 계측·판정은 오케스트레이터 직접.
- **codex challenge 3회** — P1 5 · P2 2, 전건 처분(수정 6 · 기각 1). 기각 1 = 「BL-591 강등
  반대」: `backlog.md:128` P1 정의(알려진 재발 패턴)에 자연 발화 0회인 D1/D2 가 비해당 +
  재개 조건이 그 위험을 직접 덮음. codex 반증(코드 대조로 뒤집힌 finding) **0건**.
- **B1**([BL-594]): compose `--auto-aof-rewrite-min-size 8mb`(채택 1 · 기각 3 전부 실측 근거) +
  게이트 C5⑸ `aof_ok`(수집 timeout 가드 · 분류기는 `redis_aof_readability.py` 모듈 + 실측
  캡처 7형 15테스트) + 스크래치 컨테이너 8상태 e2e.
- **C**([BL-591]/[ADR-023]): P1→P2 강등(3면 동기) + ADR-023 §재판정 신설(Proposed 유지 ·
  재개 조건 원문 보존 · A 결과 비의존 서술) + roadmap P별 내역 실측 갱신.
- **D**([BL-596]): 라벨 어휘 3분할 frozenset + 미지/결손 라벨 → `UNKNOWN 측정불가`(래칫 순서
  FAIL→C5 로 사면 불가) + 출처(archive/at/session) 보존 보고 + 동결·변이 검증.
- **A**: 노출 12.28h 에서 사전등록 4관측량 전건 충족 → **[ADR-025] Accepted**
  (①0건/p≈0.020 · ②0건 · ③84건 · ④+223). 전문 = [ADR-025 §판정](../decisions/025-conditional-fill-ownership.md).
- **B2**: `stop→flatten`(FLAT=YES) → down → pin `3a90f80c` → up. celery ready
  `2026-08-06T01:06:15Z` = 새 T0. redis 신설정 적용 실측(`config get` = 8388608) · 새 세션
  `c160a1a9` · 게이트 실격 0 · **누적 12.75h 연속**(재고정은 연속 창만 끊는다 — predicate 명세 실증).

## 게이트 (전부 커밋 후 · 조용한 트리 · 파이프 없이)

- `final-gates.sh --run night0805` **2차 전건 통과(exit 0)** @ `bea5ce59` — BE pytest
  **4199 passed / 45 skipped**(baseline 4172 + 신규 27) · e2e design-canon 32 · **authed 69 전건** ·
  CI 재현 4종 · signal 3종. 1차(exit 1)의 유일 red 가 위 반증 3(= [BL-597]).
- `bl-audit.sh` / `docs-audit.sh` 전 커밋마다 exit 0. 리뷰 2축(Standards/Spec) — scope creep 0 ·
  금지 4종(분류기 무접촉 · predicate `:185` 무접촉 · 사전등록 블록 무접촉 · 게이트 관대화 금지)
  전수 준수 확인. Standards 관측: `QB_REDIS_CONTAINER` 는 `.env.example` 미등재(기존 QB\_\* 3종과
  같은 패턴 — 스코프 판단은 사용자 몫) · AOF 표 4중 복제 · `label_buckets` 원시 dict 3곳 재계산.
- 소크: 밤새 **실격 0 · phantom 0 · 자동 사망 0**. 신설 C5 2항 프로덕션 ✓.

## 남긴 것

- [BL-597](../backlog.md#bl-597) 신규 — e2e authed 가 소크 상태와 결합(열린 포지션 → 로케이터 오염).
- [BL-594] 잔여 관측: 페이로드 손상은 `redis-check-aof` 가 못 본다(사본 기동 오라클 후보) ·
  AOF 프로브 ↔ rewrite 경합(fail-closed 방향 · 추정 ~0.1%/일) · `aof_rewrites` 실발동 며칠 관측.
- 스크래치 컨테이너 3개 정지 상태(`docker rm qb-b1-redis-test qb-b1-redis-test2 qb-b1-redis-cmd`
  — 하네스가 차단해 사람 몫. 포트 미점유 · 프로덕션과 무접촉).
- 24h 창 판정(①의 p≈0.0005)은 재기동이 연속 창을 끊어 도달하지 않음 — 12h 단독 판정임을
  [ADR-025 §판정]에 명기.
