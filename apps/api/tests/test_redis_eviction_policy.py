# Redis 축출 정책이 큐·락을 지우지 못하게 원장(=compose)에서 못박는다 (2026-08-15 · S4).
"""compose Redis 는 `noeviction` 이어야 한다.

**실사고 모양** — compose 는 단일 Redis 인스턴스에
`--maxmemory 512mb --maxmemory-policy allkeys-lru` 를 걸어 두고, 그 위에서 논리 DB 를
나눠 캐시(0)/broker(1)/result(2)/락·rate-limit(3) 을 함께 썼다. 그리고 **세 곳**이
「DB 를 나눴으니 격리된다」고 적고 있었다:

- `.env.example` — 「broker burst·eviction 으로 lock 유실 방지」
- `docs/development/docker-compose-guide.md` — 「Celery 큐는 별도 DB로 분리」
- `core/config.py` 의 `redis_lock_url` description — 「격리된 DB 3 사용」

★**전부 거짓이다.** `maxmemory-policy` 는 **인스턴스 전역**이고, Redis 의 축출 후보 선정은
논리 DB 를 구분하지 않는다(`allkeys-*` 는 말 그대로 all keys 다). ⇒ 메모리 압박이 오면
broker 메시지와 `ws:lease` 분산 락이 캐시 키와 **똑같이** 지워질 수 있었다.
`task_acks_late=True` 로도 복구되지 않는다 — 브로커에서 사라진 메시지에는 재배달할 원본이 없다.

★**이 테스트가 재는 것은 「정책 문자열」이지 런타임이 아니다.** 런타임 `CONFIG GET` 은
컨테이너가 떠 있어야 하고 CI 에서는 compose 를 안 띄운다. 원장(compose 파일)을 재는 것이
이 결함의 재발을 막는 **가장 상류**다 — 실제로 결함은 그 한 줄에 있었다.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_COMPOSE = _REPO_ROOT / "infra" / "compose" / "docker-compose.yml"

# 큐·락을 지울 수 있는 정책. `volatile-*` 도 위험하다 — 이 앱의 락과 celery result 는
# TTL 이 붙어 있어 `volatile-*` 의 **1순위 후보**다.
_EVICTING_POLICIES = (
    "allkeys-lru",
    "allkeys-lfu",
    "allkeys-random",
    "volatile-lru",
    "volatile-lfu",
    "volatile-random",
    "volatile-ttl",
)


def _redis_command_lines() -> list[str]:
    text = _COMPOSE.read_text()
    return [line for line in text.splitlines() if "redis-server" in line]


@pytest.mark.skipif(not _COMPOSE.exists(), reason="compose 파일이 없는 체크아웃")
def test_compose_redis_never_evicts() -> None:
    """★양성 — 축출 정책이 되돌아오면 red."""
    lines = _redis_command_lines()
    assert lines, (
        "compose 에서 `redis-server` 명령을 하나도 못 찾았다 — 배선이 바뀌었는지 확인해라. "
        "이 단언이 없으면 서비스가 사라진 순간 감사가 **항상 통과**한다(빈 입력 fail-open)."
    )
    for line in lines:
        policy = re.search(r"--maxmemory-policy\s+(\S+)", line)
        assert policy is not None, (
            f"`--maxmemory-policy` 를 명시해라 (redis 기본값은 noeviction 이지만 명시가 계약이다): {line.strip()}"
        )
        assert policy.group(1) not in _EVICTING_POLICIES, (
            f"Redis 축출 정책이 `{policy.group(1)}` 이다 — 이 인스턴스는 Celery broker/result 와 "
            "분산 락을 담고 있고, 논리 DB 분리는 축출에서 **아무것도 격리하지 않는다**. "
            "축출되면 큐 메시지에는 재배달할 원본이 없고 `ws:lease` 는 correctness fallback 이 "
            "없다. `noeviction` 을 써라 (2026-08-15 surface-truth S4)."
        )


def test_dead_cache_redis_setting_stays_removed() -> None:
    """★죽은 설정이 되살아나지 않게 한다.

    `redis_url`(DB 0 「캐시」)은 선언·주입은 돼 있었지만 `src/` 참조가 **0건**이었다.
    죽은 설정의 비용은 0 이 아니다 — 그 값이 compose·CI·env 6곳을 돌면서 「캐시 DB 가
    따로 있다」는 그림을 유지했고, 그 그림이 위 축출 격리 오해를 떠받쳤다.

    캐시가 정말 필요해지면 **별도 인스턴스**로 도입해라. 같은 인스턴스에 LRU 를 섞으면
    위 결함이 그대로 돌아온다.
    """
    from src.core.config import Settings

    assert "redis_url" not in Settings.model_fields, (
        "`redis_url` 이 다시 생겼다. 캐시를 도입하는 것이라면 **별도 Redis 인스턴스**여야 하고, "
        "그때 이 테스트의 문구를 함께 고쳐라 (2026-08-15 surface-truth S4)."
    )


def test_lock_url_description_does_not_promise_eviction_isolation() -> None:
    """★거짓 문장이 되돌아오지 않게 한다 (음성 대조가 아니라 **반증 고정**이다).

    코드를 고쳐도 설명이 남으면 다음 사람이 같은 오해를 이어받는다. 이 레포는 「원장이 적은
    처방의 대상이 실재하지 않는」 사고를 반복해서 겪었고, 그 뿌리는 대개 이런 문장이었다.
    """
    from src.core.config import Settings

    description = Settings.model_fields["redis_lock_url"].description or ""
    assert "격리된 DB 3" not in description, (
        "`redis_lock_url` description 이 다시 「격리」를 약속한다 — 논리 DB 는 축출을 격리하지 "
        "않는다. 격리의 근거는 compose 의 `noeviction` 이다."
    )


def test_compose_healthcheck_actually_probes_writes() -> None:
    """★`noeviction` 의 대가를 **관측 가능**하게 유지한다 (2026-08-15 적대 리뷰).

    OOM 아래에서 읽기는 되고 쓰기만 거부되는데 `redis-cli ping` 은 그때도 PONG 을 낸다.
    쓰기 프로브가 없으면 기동 후 OOM 이 **「정상」으로 관측**되고
    `QbRedisLockPoolUnhealthy` 도 발화하지 않는다 — `common/redis_client.py` 의
    SET+GET+DEL 왕복은 **lifespan startup 1회**뿐이다.

    ★이 테스트가 없으면 healthcheck 를 `ping` 으로 되돌리는 변경이 조용히 통과한다.
      실제로 이 회차의 커밋 주석이 「healthcheck 가 그 상태를 잡는다」고 **거짓 주장**했고,
      적대 리뷰가 그것을 잡았다.
    """
    text = _COMPOSE.read_text()
    block_start = text.index("  redis:\n")
    block = text[block_start : text.index("\n  backend-worker:", block_start)]
    healthcheck = block[block.index("healthcheck:") :]
    assert "redis-cli set" in healthcheck, (
        "redis healthcheck 가 쓰기를 재지 않는다 — PING 은 OOM 에서도 PONG 이다. "
        f"현재: {healthcheck[:200]}"
    )
