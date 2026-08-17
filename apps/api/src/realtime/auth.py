# HTTP와 WebSocket에서 공유하는 인증 검증 — Better Auth 가 발급한 JWT 를 JWKS 로 검증한다(ADR-034).
# ★백엔드는 비밀을 하나도 쥐지 않는다. 검증은 공개 키로 하고, 키는 `settings.jwks_url` 에서 받아
#   `kid` 별로 캐시한다. 모르는 `kid` 가 오면 PyJWKClient 가 알아서 한 번 다시 받아온다.
from __future__ import annotations

import logging
from typing import Any, Protocol

import anyio
import jwt
from jwt import PyJWKClient

from src.auth.exceptions import InvalidTokenError, UserInactiveError
from src.auth.schemas import CurrentUser
from src.auth.service import UserService
from src.core.config import settings

logger = logging.getLogger(__name__)

# ★알고리즘을 하나로 고정한다. Better Auth JWT 플러그인의 기본이 EdDSA(Ed25519)이고,
#   허용 목록을 넓히면 「서명이 없는 것과 같은」 알고리즘 혼동 공격 표면이 열린다.
#   양쪽을 우리가 소유하므로 넓힐 이유가 없다 — 바꾸려면 FE `lib/auth.ts` 와 **함께** 바꿔라.
ALGORITHMS = ["EdDSA"]

_jwk_client: PyJWKClient | None = None
_jwk_client_url: str | None = None


class Requestish(Protocol):
    """헤더만 있으면 되는 오리 타입 — WebSocket 경로가 `SimpleNamespace` 를 넘긴다.

    ★`headers` 는 **읽기 전용**으로 선언한다. 설정 가능한 변수로 두면 Starlette 의
    `Request.headers`(property)가 프로토콜을 만족하지 못한다.
    """

    @property
    def headers(self) -> Any: ...


def _client() -> PyJWKClient:
    """JWKS 클라이언트 싱글톤. URL 이 바뀌면(테스트 monkeypatch) 새로 만든다."""
    global _jwk_client, _jwk_client_url
    url = settings.jwks_url
    if _jwk_client is None or _jwk_client_url != url:
        # `cache_keys=True` 가 kid → key 매핑을 들고 있고, 모르는 kid 를 만나면 재조회한다.
        _jwk_client = PyJWKClient(url, cache_keys=True, lifespan=3600)
        _jwk_client_url = url
    return _jwk_client


def reset_jwks_cache() -> None:
    """테스트 전용 — 프로세스 간 캐시 누수를 막는다."""
    global _jwk_client, _jwk_client_url
    _jwk_client = None
    _jwk_client_url = None
    # ★kid 캐시도 함께 비운다 — 안 비우면 앞 테스트가 등록한 kid 가 남아
    # 「모르는 kid 는 네트워크를 안 탄다」는 단언이 **순서 의존**으로 초록이 된다.
    _KNOWN_KIDS.clear()


def _decode(token: str) -> dict[str, Any]:
    """서명·만료·iss·aud 를 한 번에 검증하고 payload 를 돌려준다. 실패는 전부 예외다.

    ★**동기 함수다.** `PyJWKClient` 는 urllib 로 JWKS 를 가져오므로 이벤트 루프에서 직접 부르면
    첫 요청(과 키 회전 시점)에 루프가 막힌다. 호출부가 스레드로 넘긴다.
    """
    signing_key = _client().get_signing_key_from_jwt(token)
    issuer = settings.better_auth_url.rstrip("/")
    payload: dict[str, Any] = jwt.decode(
        token,
        signing_key.key,
        algorithms=ALGORITHMS,
        issuer=issuer,
        audience=issuer,
        options={"require": ["exp", "sub", "iss", "aud"]},
    )
    # 검증에 성공한 kid 만 기억한다 — `verified_subject_or_none` 이 이걸 보고
    # **네트워크를 타지 않아도 되는지** 판단한다(아래 그 함수 머리말 참조).
    kid = _unverified_kid(token)
    if kid and len(_KNOWN_KIDS) < _KNOWN_KID_CAP:
        _KNOWN_KIDS.add(kid)
    return payload


# 검증에 한 번이라도 성공한 kid. 값의 출처가 **우리 JWKS 하나**라 실제로는 1~2개다.
# 상한은 「어떤 경로로도 무한히 자라지 않는다」를 코드로 못 박기 위한 것이다.
_KNOWN_KIDS: set[str] = set()
_KNOWN_KID_CAP = 32


def _unverified_kid(token: str) -> str | None:
    """서명을 **검증하지 않고** 헤더의 `kid` 만 읽는다. 네트워크도 crypto 도 없다.

    ★이 값을 신뢰 판단에 쓰면 안 된다 — 공격자가 고른 문자열이다. 여기서는 오직
    「이미 아는 kid 인가」를 묻는 **캐시 조회 키**로만 쓴다.
    """
    try:
        return jwt.get_unverified_header(token).get("kid")
    except Exception:
        return None


def verified_claims_or_none(request: Requestish) -> dict[str, Any] | None:
    """검증된 JWT payload 를 통째로 돌려준다. **DB 를 안 친다.** ([BL-754] · [BL-784])

    ★rate limit 이 「누구인가」를 알아야 하는데, `authenticate_token` 은 사용자 행을
    **프로비저닝까지** 한다. 그것을 미들웨어에서 부르면 인증 dependency 보다 먼저
    DB 에 행을 만들고 매 요청에 왕복이 붙는다. 여기서는 `_decode` 만 재사용한다 —
    **검증기는 여전히 이 파일 하나다**(`apps/api/AGENTS.md` §2).

    ★실패는 전부 `None` 이다. 이 함수는 **문을 지키지 않는다** — 문은 인증 dependency 다.
    토큰이 없거나 깨졌으면 rate limit 이 IP 로 떨어질 뿐이고, 요청 자체는 dependency 가 막는다.

    ★★**네트워크를 절대 타지 않는다**(2026-08-16 codex 적대 리뷰 P1). 이 함수는 rate limit
    **앞**에서 돌기 때문에, 여기서 JWKS 를 가져오면 한도의 보호를 못 받는 외부 I/O 가 생긴다.
    실측: `PyJWKClient` 는 **미상 `kid` 에 음성 캐시가 없어** 같은 가짜 kid 를 10번 보내면
    JWKS 를 **11번** 가져온다 — 즉 `Authorization: Bearer <아무거나>` 만으로 1:1 증폭이다.
    ⇒ **이미 검증에 성공한 적 있는 `kid` 일 때만** `_decode` 를 부른다. 그 kid 는 캐시에 있어
    조회가 끝나고, 모르는 kid 는 `None` 으로 떨어져 IP 버킷을 쓴다.
    대가는 **정상 사용자의 첫 요청 1건이 IP 버킷**이라는 것뿐이다 — 그 요청의 인증
    dependency 가 정식으로 검증하며 kid 를 등록하므로 두 번째 요청부터 per-user 로 간다.
    """
    try:
        token = _bearer_token(request)
    except InvalidTokenError:
        return None
    kid = _unverified_kid(token)
    if kid is None or kid not in _KNOWN_KIDS:
        return None
    try:
        return _decode(token)
    except Exception:
        return None


def verified_subject_or_none(request: Requestish) -> str | None:
    """검증된 JWT `sub` 만 돌려준다. `verified_claims_or_none` 의 얇은 래퍼다.

    ★검증 경로를 새로 만들지 않는다 — payload 가 필요한 호출부(rate limit 완화 판정)와
    `sub` 만 필요한 호출부가 **같은 한 번의 검증**을 나눠 쓴다. 토큰 하나에 crypto 를
    두 번 돌리지 않기 위해서다.
    """
    payload = verified_claims_or_none(request)
    if payload is None:
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None


def _bearer_token(request: Requestish) -> str:
    """`Authorization: Bearer <token>` 에서 토큰만 뽑는다."""
    headers = request.headers
    raw = headers.get("authorization") or headers.get("Authorization")
    if not raw:
        raise InvalidTokenError(reason="missing_authorization_header")
    scheme, _, token = str(raw).partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise InvalidTokenError(reason="malformed_authorization_header")
    return token.strip()


async def authenticate_request(request: Requestish, service: UserService) -> CurrentUser:
    """요청의 Bearer JWT 를 검증하고 로컬 사용자를 lazy-create 한다."""
    return await authenticate_token(_bearer_token(request), service)


async def authenticate_token(token: str, service: UserService) -> CurrentUser:
    """토큰 문자열을 검증하고 로컬 사용자를 lazy-create 한다.

    ★인증과 프로비저닝이 한 함수에 있는 것은 Clerk 시절과 같다 — 사용자 행은 첫 인증 요청에서
    생긴다(웹훅이 없다). 그래서 `auth_subject` 는 JWT `sub` 이고 우리 `users.id` 와 별개다.
    """
    try:
        payload = await anyio.to_thread.run_sync(_decode, token)
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError(reason="expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise InvalidTokenError(reason="issuer_mismatch") from exc
    except jwt.InvalidAudienceError as exc:
        raise InvalidTokenError(reason="audience_mismatch") from exc
    except jwt.PyJWKClientError as exc:
        # 알 수 없는 kid · JWKS 취득 실패. ★원문을 응답에 싣지 않는다 — 로그로만 남긴다.
        logger.warning("jwks_lookup_failed error=%s", exc)
        raise InvalidTokenError(reason="jwks_unavailable") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError(reason="invalid_signature") from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError(reason="missing_sub")

    user = await service.get_or_create(
        auth_subject=str(subject),
        email=payload.get("email"),
        username=payload.get("username"),
        country_code=payload.get("country"),
    )
    if not user.is_active:
        raise UserInactiveError()

    return CurrentUser.model_validate(user)
