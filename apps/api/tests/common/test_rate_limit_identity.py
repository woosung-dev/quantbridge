"""[BL-754] rate limit 이 프록시 뒤에서 전 사용자 공용 버킷으로 붕괴하지 않는다.

★**이 파일이 재는 것은 「누구인가」를 언제 아는가다.** 종전 `rate_limit_key` 는
`request.state.user_id` 를 읽었는데 그것을 **세우는 코드가 레포에 0건**이었다. 그래서
실제로는 항상 IP 갈래였고, Cloudflare 뒤에서는 모든 사용자의 `client.host` 가 같아서
한 사람이 한도를 태우면 **전원이 429** 였다.

원장의 처방 「auth dependency 한 줄」은 성립하지 않는다 — `SlowAPIMiddleware` 는 ASGI 라
라우트 dependency 보다 먼저 돌고, 그 시점엔 `state.user_id` 가 없다. 그래서 수리는
`_RateLimitIdentityMiddleware` 를 **`SlowAPIMiddleware` 바깥에** 세우는 것이고,
이 파일의 첫 테스트가 **그 순서**를 직접 잰다.

전달 헤더 축의 음성 대조도 여기 있다 — Cloudflare 는 기존 `X-Forwarded-For` 를 덮어쓰지
않고 **뒤에 붙이므로** leftmost 는 클라이언트가 심을 수 있다. `CF-Connecting-IP` 가 먼저다.
"""

from __future__ import annotations

import ipaddress

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter

from src.common.rate_limit import install_rate_limit


def _install_limiter(monkeypatch: pytest.MonkeyPatch, default_limits: list[str]) -> Limiter:
    """memory:// + 주어진 default_limits 로 module-level limiter 를 교체한다.

    `key_func` 는 **프로덕션 `rate_limit_key` 그대로**다 — 그것을 lambda 로 갈아끼우면
    이 파일이 재는 것이 사라진다(종전 `test_per_user_isolation` 이 그랬다).
    """
    from src.common import rate_limit as rl

    mem = Limiter(
        key_func=rl.rate_limit_key,
        storage_uri="memory://",
        default_limits=default_limits,
        swallow_errors=True,
        headers_enabled=True,
        in_memory_fallback_enabled=False,
        strategy="fixed-window",
    )
    monkeypatch.setattr(rl, "limiter", mem)
    return mem


@pytest.fixture
def app_with_identity(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """★**데코레이터 없는** 엔드포인트 + `default_limits=1/minute`.

    ★★**이 선택이 이 파일의 판별력 그 자체다**(2026-08-16 변이로 확인).
    `@limiter.limit(...)` 이 붙은 엔드포인트는 slowapi 가 키를 **핸들러 래퍼 안**에서
    계산한다 — 그때는 미들웨어가 어느 순서든 `state.user_id` 가 이미 세팅돼 있어서
    **순서를 뒤집는 변이가 초록으로 통과한다.** 초판이 정확히 그렇게 무증거였다.
    순서가 갈리는 곳은 `SlowAPIMiddleware` 가 집행하는 `default_limits` 뿐이다.
    """
    _install_limiter(monkeypatch, ["1/minute"])

    app = FastAPI()
    app.state.redis_lock_healthy = True
    install_rate_limit(app)

    # ★데코레이터를 **붙이지 않는다** — default_limits 갈래로 떨어뜨린다.
    @app.get("/guarded")
    async def guarded(request: Request, response: Response) -> dict[str, str]:
        return {"key_scope": "user" if getattr(request.state, "user_id", None) else "ip"}

    return app


def _stub_subject(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, str]) -> None:
    """Bearer 토큰 → subject 사상을 심는다. JWT 검증 자체는 realtime/auth 테스트가 잰다."""

    def _fake(request: object) -> str | None:
        raw = request.headers.get("authorization", "")  # type: ignore[attr-defined]
        token = raw.partition(" ")[2].strip()
        return mapping.get(token)

    monkeypatch.setattr("src.realtime.auth.verified_subject_or_none", _fake)


# ─────────────────────────────────────────────────────
# ① 순서 — Identity 가 SlowAPI 보다 먼저 도는가
# ─────────────────────────────────────────────────────


def test_identity_runs_before_slowapi(
    app_with_identity: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★`SlowAPIMiddleware` 가 키를 계산하는 시점에 이미 신원이 있어야 한다.

    응답의 `key_scope` 는 핸들러가 본 값이라 **순서를 증명하지 못한다** — 미들웨어가
    SlowAPI 안쪽에 있어도 핸들러 시점엔 세팅돼 있기 때문이다. 그래서 **버킷이 갈리는지**로
    잰다: 서로 다른 두 토큰이 같은 client.host 에서 와도 둘 다 200 이면 키가 신원으로
    갈린 것이고, 순서가 틀렸다면 두 번째가 429 다. 이 판별은 `default_limits` 갈래
    (= 데코레이터 없는 엔드포인트)에서만 성립한다 — fixture 독스트링 참조.
    """
    _stub_subject(monkeypatch, {"tok-a": "sub-A", "tok-b": "sub-B"})

    with TestClient(app_with_identity) as client:
        a1 = client.get("/guarded", headers={"authorization": "Bearer tok-a"})
        b1 = client.get("/guarded", headers={"authorization": "Bearer tok-b"})
        a2 = client.get("/guarded", headers={"authorization": "Bearer tok-a"})

    assert a1.status_code == 200
    assert a1.json()["key_scope"] == "user"
    # ★같은 client.host 인데도 다른 사용자는 자기 한도를 갖는다 — 이것이 이 항목의 수리다.
    assert b1.status_code == 200, "두 번째 사용자가 첫 사용자의 한도에 걸렸다 — 공용 버킷 붕괴"
    # 같은 사용자의 두 번째 요청은 자기 한도에 걸린다.
    assert a2.status_code == 429


def test_unauthenticated_still_collapses_to_ip(
    app_with_identity: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★음성 대조 — 토큰이 없으면 여전히 IP 한 버킷이다.

    이 단언이 없으면 위 테스트의 초록이 「신원으로 갈렸다」가 아니라 「한도가 아예 안 걸린다」
    여도 통과한다. 두 개가 한 쌍이다.
    """
    _stub_subject(monkeypatch, {})

    with TestClient(app_with_identity) as client:
        r1 = client.get("/guarded")
        r2 = client.get("/guarded")

    assert r1.status_code == 200
    assert r1.json()["key_scope"] == "ip"
    assert r2.status_code == 429


def test_invalid_token_falls_back_to_ip_and_does_not_reject(
    app_with_identity: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★미들웨어는 문을 지키지 않는다 — 깨진 토큰에 401 을 내면 안 된다.

    거부는 인증 dependency 의 일이다. 여기서 막으면 공개 엔드포인트(`/waitlist` 등)가 죽는다.
    """
    _stub_subject(monkeypatch, {})  # 어떤 토큰도 subject 로 안 풀린다

    with TestClient(app_with_identity) as client:
        r = client.get("/guarded", headers={"authorization": "Bearer garbage"})

    assert r.status_code == 200, "검증 실패 토큰이 요청을 막았다 — 미들웨어가 문을 지키고 있다"
    assert r.json()["key_scope"] == "ip"


# ─────────────────────────────────────────────────────
# ② 신원 추출 자체 — 위 테스트들은 stub 을 쓰므로 여기서 실물을 잰다
# ─────────────────────────────────────────────────────


def test_verified_subject_extracts_sub_from_verified_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★위 세 테스트는 `verified_subject_or_none` 을 **stub** 한다 — 그것만 두면
    이 함수를 `return None` 으로 만드는 변이가 **전건 초록**이다(2026-08-16 실측).
    여기서는 검증기(`_decode`)만 대신하고 **`sub` 추출과 실패 처리는 실물**을 태운다.
    """
    from src.realtime import auth as ra

    monkeypatch.setattr(ra, "_decode", lambda _t: {"sub": "sub-real", "exp": 1})
    req = _MockRequest("1.2.3.4", {"authorization": "Bearer whatever"})
    assert ra.verified_subject_or_none(req) == "sub-real"  # type: ignore[arg-type]

    # ★음성 ⑴ — payload 에 sub 가 없으면 None (키가 "user:None" 이 되면 전원 한 버킷이다).
    monkeypatch.setattr(ra, "_decode", lambda _t: {"exp": 1})
    assert ra.verified_subject_or_none(req) is None  # type: ignore[arg-type]

    # ★음성 ⑵ — 검증 실패는 예외가 아니라 None 으로 나온다(문을 안 지킨다).
    def _boom(_t: str) -> dict[str, object]:
        raise ValueError("bad signature")

    monkeypatch.setattr(ra, "_decode", _boom)
    assert ra.verified_subject_or_none(req) is None  # type: ignore[arg-type]

    # ★음성 ⑶ — Authorization 헤더가 없으면 검증기를 아예 안 부른다.
    def _must_not_run(_t: str) -> dict[str, object]:
        raise AssertionError("헤더가 없는데 검증기가 불렸다")

    monkeypatch.setattr(ra, "_decode", _must_not_run)
    assert ra.verified_subject_or_none(_MockRequest("1.2.3.4", {})) is None  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────
# ③ 전달 헤더 — CF-Connecting-IP 가 XFF leftmost 를 이긴다
# ─────────────────────────────────────────────────────


class _MockRequest:
    def __init__(self, client_host: str, headers: dict[str, str] | None = None) -> None:
        self.client = type("C", (), {"host": client_host})()
        self.headers = headers or {}


def test_cf_connecting_ip_wins_over_spoofable_xff(monkeypatch: pytest.MonkeyPatch) -> None:
    """★Cloudflare 는 XFF 를 **덮어쓰지 않고 뒤에 붙인다** — leftmost 는 클라이언트 것이다.

    공격자가 `X-Forwarded-For: 9.9.9.9` 를 심으면 Cloudflare 를 거친 뒤 XFF 는
    `9.9.9.9, <실 IP>` 가 된다. leftmost 를 키로 쓰면 **요청마다 키를 바꿔** 한도를 벗어난다.
    `CF-Connecting-IP` 는 Cloudflare 가 덮어써서 넣는 단일 값이다.
    """
    from src.common import rate_limit as rl

    monkeypatch.setattr(rl, "_TRUSTED_NETS", [ipaddress.ip_network("127.0.0.0/8")])

    spoofed = _MockRequest(
        "127.0.0.1",
        {"x-forwarded-for": "9.9.9.9, 203.0.113.7", "cf-connecting-ip": "203.0.113.7"},
    )
    assert rl._client_ip_or_xff(spoofed) == "203.0.113.7"  # type: ignore[arg-type]

    # CF 헤더가 없는 proxy 는 종전대로 XFF leftmost 를 쓴다(회귀 방지).
    plain = _MockRequest("127.0.0.1", {"x-forwarded-for": "198.51.100.5, 127.0.0.1"})
    assert rl._client_ip_or_xff(plain) == "198.51.100.5"  # type: ignore[arg-type]

    # ★음성 대조 — 신뢰 대역 밖에서 온 요청은 CF 헤더도 믿지 않는다.
    untrusted = _MockRequest("203.0.113.99", {"cf-connecting-ip": "1.1.1.1"})
    assert rl._client_ip_or_xff(untrusted) == "203.0.113.99"  # type: ignore[arg-type]
