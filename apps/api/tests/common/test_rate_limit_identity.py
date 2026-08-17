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


def _stub_subject(
    monkeypatch: pytest.MonkeyPatch,
    mapping: dict[str, str],
    emails: dict[str, str] | None = None,
) -> None:
    """Bearer 토큰 → 검증된 claims 사상을 심는다. JWT 검증 자체는 realtime/auth 테스트가 잰다.

    ★미들웨어가 부르는 것은 `verified_claims_or_none` 이다([BL-784] — 면제 판정에 `email`
    claim 이 필요해서 payload 를 통째로 받는다). `verified_subject_or_none` 을 stub 하면
    미들웨어를 **하나도 안 지난다.**
    """

    def _fake(request: object) -> dict[str, object] | None:
        raw = request.headers.get("authorization", "")  # type: ignore[attr-defined]
        token = raw.partition(" ")[2].strip()
        subject = mapping.get(token)
        if subject is None:
            return None
        claims: dict[str, object] = {"sub": subject}
        if emails is not None and token in emails:
            claims["email"] = emails[token]
        return claims

    monkeypatch.setattr("src.realtime.auth.verified_claims_or_none", _fake)


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

    # ★kid 게이트를 통과시킨다 — 이 테스트가 재는 것은 `sub` 추출이지 kid 캐시가 아니다.
    monkeypatch.setattr(ra, "_unverified_kid", lambda _t: "kid-test")
    monkeypatch.setattr(ra, "_KNOWN_KIDS", {"kid-test"})
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


# ─────────────────────────────────────────────────────
# ④ ★rate limit **앞**에서 도는 코드가 네트워크를 타면 안 된다 (codex P1, 2026-08-16)
# ─────────────────────────────────────────────────────


def test_identity_extraction_never_fetches_jwks(monkeypatch: pytest.MonkeyPatch) -> None:
    """★모르는 `kid` 는 **JWKS 를 가져오지 않는다.**

    이 함수는 `SlowAPIMiddleware` 보다 **바깥**에서 돈다 — 즉 여기서 하는 일은
    **한도의 보호를 받지 않는다.** 수리 전 실측: `PyJWKClient` 는 미상 kid 에 음성 캐시가
    없어 같은 가짜 kid 를 10번 보내면 JWKS 를 **11번** 가져왔다. `Authorization: Bearer
    <아무거나>` 만으로 우리 FE 컨테이너에 1:1 증폭이 걸린다는 뜻이다.
    """
    import base64
    import json

    from src.realtime import auth as ra

    fetched: list[str] = []

    class _Boom:
        def get_signing_key_from_jwt(self, _token: str) -> object:
            # ★raise 로 잡으면 안 된다 — `verified_subject_or_none` 의 `except Exception` 이
            #   `AssertionError` 까지 삼켜서 **양성 대조가 조용히 죽는다**(초판이 그랬다).
            #   호출 사실만 기록하고 정상 실패로 흘린다.
            fetched.append("fetch")
            raise ValueError("no key")

    monkeypatch.setattr(ra, "_client", lambda: _Boom())
    ra.reset_jwks_cache()

    def _tok(kid: str) -> str:
        enc = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()  # noqa: E731
        return f"{enc({'alg': 'EdDSA', 'kid': kid})}.{enc({'sub': 'x'})}.AAAA"

    req = _MockRequest("1.2.3.4", {"authorization": f"Bearer {_tok('UNKNOWN')}"})
    for _ in range(10):
        assert ra.verified_subject_or_none(req) is None  # type: ignore[arg-type]
    assert fetched == [], f"미상 kid 가 JWKS 를 {len(fetched)}회 가져왔다"

    # ★양성 대조 — kid 가 알려지면 실제로 검증기를 탄다. 이 단언이 없으면 위 0회는
    #   「그냥 아무것도 안 한다」와 구분되지 않는다.
    ra._KNOWN_KIDS.add("UNKNOWN")
    assert ra.verified_subject_or_none(req) is None  # type: ignore[arg-type]
    assert fetched == ["fetch"], "kid 가 알려졌는데도 검증기를 안 탔다 — 위 0회가 무증거다"


def test_successful_decode_registers_its_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    """검증에 성공하면 그 kid 가 등록돼 **다음 요청부터** per-user 로 간다."""
    from src.realtime import auth as ra

    ra.reset_jwks_cache()
    monkeypatch.setattr(ra, "_unverified_kid", lambda _t: "kid-A")
    monkeypatch.setattr(
        ra,
        "_client",
        lambda: type(
            "C", (), {"get_signing_key_from_jwt": lambda _s, _t: type("K", (), {"key": "k"})()}
        )(),
    )
    monkeypatch.setattr(ra.jwt, "decode", lambda *a, **k: {"sub": "s"})

    assert "kid-A" not in ra._KNOWN_KIDS
    ra._decode("tok")
    assert "kid-A" in ra._KNOWN_KIDS, "성공한 kid 가 등록되지 않으면 per-user 격리가 영영 안 켜진다"


# ─────────────────────────────────────────────────────
# ⑤ [BL-784] e2e 신원만 한도를 면제받는다
# ─────────────────────────────────────────────────────

E2E_EMAIL = "e2e@dogfood.local"


def _configure_exemption(
    monkeypatch: pytest.MonkeyPatch, *, email: str, app_env: str = "development"
) -> None:
    """면제 설정을 `settings` 인스턴스에 직접 심는다(Settings 재생성 비용 회피)."""
    from src.common import rate_limit as rl

    monkeypatch.setattr(rl.settings, "e2e_rate_limit_exempt_email", email)
    monkeypatch.setattr(rl.settings, "app_env", app_env)


@pytest.fixture
def app_with_exemption(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """`default_limits=1/minute` + **데코레이터 라우트**를 함께 둔 앱.

    ★한도를 1 로 낮춘 것이 이 절의 판별력이다 — 면제 안 된 신원의 두 번째 요청이 429 가
    아니면 이 절은 한도를 재고 있지 않다(수용 기준 AC-3 의 pytest 축).
    ★데코레이터 라우트를 같이 두는 이유는 「면제 플래그를 slowapi 가 미들웨어 갈래와
    데코레이터 갈래 양쪽에서 본다」는 주장이 `rate_limit.py` 주석에 있기 때문이다.
    주석의 인과는 실측 대상이다(`apps/api/AGENTS.md` §10).
    """
    mem = _install_limiter(monkeypatch, ["1/minute"])

    app = FastAPI()
    app.state.redis_lock_healthy = True
    install_rate_limit(app)

    @app.get("/guarded")
    async def guarded(request: Request, response: Response) -> dict[str, str]:
        return {"key_scope": "user" if getattr(request.state, "user_id", None) else "ip"}

    @app.get("/decorated")
    @mem.limit("1/minute")
    async def decorated(request: Request, response: Response) -> dict[str, str]:
        return {"ok": "1"}

    return app


def _codes(client: TestClient, path: str, token: str, times: int) -> list[int]:
    return [
        client.get(path, headers={"authorization": f"Bearer {token}"}).status_code
        for _ in range(times)
    ]


def test_only_the_e2e_identity_is_relaxed(
    app_with_exemption: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★AC-1 — **같은 요청**을 두 신원으로 냈을 때 한쪽만 완화된다.

    완화가 신원을 안 보면 일반 신원도 200 만 나오고, 완화가 아예 안 걸리면 e2e 신원이 429 다.
    두 단언이 한 쌍이라 어느 쪽으로 망가져도 red 다.
    """
    _configure_exemption(monkeypatch, email=E2E_EMAIL)
    _stub_subject(
        monkeypatch,
        {"tok-e2e": "sub-e2e", "tok-user": "sub-user"},
        {"tok-e2e": E2E_EMAIL, "tok-user": "someone@example.com"},
    )

    with TestClient(app_with_exemption) as client:
        e2e = _codes(client, "/guarded", "tok-e2e", 5)
        normal = _codes(client, "/guarded", "tok-user", 2)

    assert e2e == [200] * 5, f"e2e 신원이 한도에 걸렸다 — 완화가 발화하지 않는다: {e2e}"
    assert normal == [200, 429], f"일반 신원까지 완화됐다면 한도가 사라진 것이다: {normal}"


def test_relaxation_also_covers_decorated_routes(
    app_with_exemption: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`@limiter.limit(...)` 이 붙은 라우트도 같은 플래그로 면제된다.

    ★authed 스위트가 실제로 치는 경로에 `/api/v1/backtests`(`10/minute` 데코레이터)가 있다.
    미들웨어 갈래만 면제하면 그 축이 남는다.
    """
    _configure_exemption(monkeypatch, email=E2E_EMAIL)
    _stub_subject(
        monkeypatch,
        {"tok-e2e": "sub-e2e", "tok-user": "sub-user"},
        {"tok-e2e": E2E_EMAIL, "tok-user": "someone@example.com"},
    )

    with TestClient(app_with_exemption) as client:
        e2e = _codes(client, "/decorated", "tok-e2e", 3)
        normal = _codes(client, "/decorated", "tok-user", 2)

    assert e2e == [200] * 3, f"데코레이터 갈래가 면제되지 않았다: {e2e}"
    assert normal == [200, 429], f"데코레이터 한도 자체가 안 걸린다 — 위 초록이 무증거다: {normal}"


def test_production_config_never_relaxes(
    app_with_exemption: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★★AC-2 — production 구성에서는 **같은 신원·같은 설정**이어도 완화가 발화하지 않는다.

    이 레인의 핵심 위험이 「프로덕션 경로로 새는 것」이다. 설정과 신원을 완화 성립 조건 그대로
    두고 `app_env` 하나만 production 으로 돌린다 — 그러면 429 가 돌아와야 한다.
    """
    _configure_exemption(monkeypatch, email=E2E_EMAIL, app_env="production")
    _stub_subject(monkeypatch, {"tok-e2e": "sub-e2e"}, {"tok-e2e": E2E_EMAIL})

    with TestClient(app_with_exemption) as client:
        codes = _codes(client, "/guarded", "tok-e2e", 2)

    assert codes == [200, 429], f"production 에서 완화가 발화했다: {codes}"


def test_unset_exemption_relaxes_nobody(
    app_with_exemption: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★AC-2 — 설정이 **빈 값**이면 어떤 신원도 면제되지 않는다(기본 배포 상태).

    빈 설정이 「전부 면제」로 뒤집히는 것이 이 판정의 유일한 파국이라 별도로 잰다.
    """
    _configure_exemption(monkeypatch, email="")
    _stub_subject(monkeypatch, {"tok-e2e": "sub-e2e"}, {"tok-e2e": E2E_EMAIL})

    with TestClient(app_with_exemption) as client:
        codes = _codes(client, "/guarded", "tok-e2e", 2)

    assert codes == [200, 429], f"설정이 비었는데 완화가 발화했다: {codes}"


@pytest.mark.parametrize(
    ("configured", "claimed", "expected"),
    [
        # ── 면제로 오인될 수 있는 값들 ──────────────────────────────
        ("", E2E_EMAIL, False),  # 미설정
        ("   ", E2E_EMAIL, False),  # 공백뿐 — strip 후 빈 값
        ("", "", False),  # 양쪽 다 빔 — "" == "" 로 통과하면 전원 면제다
        ("", None, False),  # claim 자체가 없음
        (E2E_EMAIL, None, False),  # 설정만 있고 신원에 email claim 이 없다
        (E2E_EMAIL, "", False),  # email claim 이 빈 문자열
        (E2E_EMAIL, "e2e@dogfood.local.attacker.test", False),  # 접두 일치
        (E2E_EMAIL, "attacker+e2e@dogfood.local", False),  # 부분 문자열 포함
        (E2E_EMAIL, "someone@example.com", False),  # 다른 계정
        # ── 걸려야 하는 값들(양성 대조) ────────────────────────────
        (E2E_EMAIL, E2E_EMAIL, True),
        ("E2E@Dogfood.Local", E2E_EMAIL, True),  # 설정 쪽 대소문자 변형
        (E2E_EMAIL, "  E2E@DOGFOOD.LOCAL  ", True),  # claim 쪽 공백 + 대문자
    ],
)
def test_exempt_predicate_value_table(
    monkeypatch: pytest.MonkeyPatch, configured: str, claimed: str | None, expected: bool
) -> None:
    """판정식 자체의 값 표. 배선은 위 4개 테스트가 잰다(순수 함수 정확성 ≠ 배선)."""
    from src.common import rate_limit as rl

    monkeypatch.setattr(rl.settings, "e2e_rate_limit_exempt_email", configured)
    monkeypatch.setattr(rl.settings, "app_env", "development")
    assert rl.is_rate_limit_exempt_identity(claimed) is expected

    # ★production 에서는 위 표의 **참 케이스까지 전부** 거짓이다 — 한 줄로 같이 잰다.
    monkeypatch.setattr(rl.settings, "app_env", "production")
    assert rl.is_rate_limit_exempt_identity(claimed) is False
