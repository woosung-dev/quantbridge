"""Sprint 24 BL-013 — WebSocket auth/network circuit breaker.

codex G.0 P1 #3 (Sprint 24): failures counter 와 blocked TTL **분리 + 정책 명문화**.
- `BybitAuthError` (인증 거부) → **즉시 block** (`ws:auth:blocked:{account_id}` SET PX 3_600_000)
  운영자 manual fix 필요 (API key 회전 / IP whitelist 등). Beat 5분 재시도 noise 차단.
- network/timeout/ConnectionClosed (일시 장애) → `ws:auth:failures:{account_id}` INCR + EXPIRE 600s
  3 회 누적 시 block. supervisor 자동 reconnect (1→30s) 가 transient 흡수.

Circuit breaker open 중:
- `_stream_main` 진입 시 즉시 skip (Slack alert 0 — 이미 block 시점에 1회 send 됨)
- TTL 3600s 만료 후 자동 재개 (operator 별도 조치 없이)

수동 해제 (runbook):
```bash
# Block + counter 모두 삭제
docker exec quantbridge-redis redis-cli -n 3 DEL ws:auth:blocked:{account_id} ws:auth:failures:{account_id}
```

Sprint 24 BL-016 (first_connect race): 본 모듈의 `record_network_failure()` 를
재사용 — first_connect timeout 발생 횟수도 동일 counter 에 누적.
"""
from __future__ import annotations

import logging

from src.common.metrics import qb_ws_auth_circuit_total
from src.common.redis_client import get_redis_lock_pool

logger = logging.getLogger(__name__)

# TTL 정책 (codex G.0 P1 #3 명문화)
_BLOCKED_TTL_MS = 3_600_000  # 1h — auth fail / network 3회 누적 시
_FAILURES_TTL_MS = 600_000  # 10min — counter sliding window
_NETWORK_FAILURE_THRESHOLD = 3  # network failures 누적 시 block


def _blocked_key(account_id: str) -> str:
    return f"ws:auth:blocked:{account_id}"


def _failures_key(account_id: str) -> str:
    return f"ws:auth:failures:{account_id}"


async def is_circuit_open(account_id: str) -> bool:
    """Circuit breaker open 상태 check — `_run_async` 진입 시 호출.

    True → stream 시작 안 함, skip + duplicate 처리. False → 정상 진입.
    Redis 장애 시 보수적으로 False 반환 (false-positive 방지 — auth fail 까지
    시도 후 정확히 차단).
    """
    pool = get_redis_lock_pool()
    try:
        result = await pool.exists(_blocked_key(account_id))
        return bool(result)
    except Exception as exc:
        logger.warning(
            "ws_circuit_check_failed account=%s err=%s — assume closed (보수적)",
            account_id,
            exc,
        )
        return False


async def record_auth_failure(account_id: str) -> None:
    """BybitAuthError 즉시 block. counter 사용 안 함 (auth 거부는 retry 무의미).

    `ws:auth:blocked:{account_id}` SET PX 3_600_000.
    """
    pool = get_redis_lock_pool()
    try:
        await pool.set(_blocked_key(account_id), b"1", px=_BLOCKED_TTL_MS)
        # failures counter 도 reset (정합)
        await pool.delete(_failures_key(account_id))
        qb_ws_auth_circuit_total.labels(outcome="block_auth").inc()
        logger.warning(
            "ws_circuit_opened reason=auth account=%s ttl_ms=%d",
            account_id,
            _BLOCKED_TTL_MS,
        )
    except Exception as exc:
        logger.warning(
            "ws_circuit_record_auth_failed account=%s err=%s", account_id, exc
        )


async def record_network_failure(account_id: str) -> bool:
    """network/timeout/ConnectionClosed 1회 누적 — 3회 시 block.

    Returns True if circuit opened (3회 도달), False otherwise.
    """
    pool = get_redis_lock_pool()
    try:
        new_count = await pool.incr(_failures_key(account_id))
        # EXPIRE 매번 재설정 — sliding window (마지막 failure 후 10분 동안만 누적)
        await pool.expire(_failures_key(account_id), _FAILURES_TTL_MS // 1000)
        qb_ws_auth_circuit_total.labels(outcome="network_failure").inc()

        if new_count >= _NETWORK_FAILURE_THRESHOLD:
            await pool.set(_blocked_key(account_id), b"1", px=_BLOCKED_TTL_MS)
            await pool.delete(_failures_key(account_id))
            qb_ws_auth_circuit_total.labels(outcome="block_network").inc()
            logger.warning(
                "ws_circuit_opened reason=network_threshold account=%s "
                "count=%d ttl_ms=%d",
                account_id,
                new_count,
                _BLOCKED_TTL_MS,
            )
            return True
        logger.info(
            "ws_circuit_network_failure account=%s count=%d/%d",
            account_id,
            new_count,
            _NETWORK_FAILURE_THRESHOLD,
        )
        return False
    except Exception as exc:
        logger.warning(
            "ws_circuit_record_network_failed account=%s err=%s",
            account_id,
            exc,
        )
        return False


async def reset_circuit(account_id: str) -> None:
    """수동 해제용 helper — admin endpoint 또는 runbook.

    `redis-cli DEL` 직접 가능하나, audit log + metric 위해 본 helper 권장.
    """
    pool = get_redis_lock_pool()
    try:
        await pool.delete(_blocked_key(account_id), _failures_key(account_id))
        qb_ws_auth_circuit_total.labels(outcome="restored").inc()
        logger.info("ws_circuit_reset account=%s", account_id)
    except Exception as exc:
        logger.warning("ws_circuit_reset_failed account=%s err=%s", account_id, exc)
