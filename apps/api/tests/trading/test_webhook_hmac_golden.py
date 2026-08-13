"""Sprint 13 Phase B HMAC golden vector — codex G.0 2차 P1 critical.

BE/FE 동일 hex 보장으로 byte-level drift 차단.
FE `test-order-dialog.test.tsx` 의 EXPECTED_HEX 와 반드시 동일해야 한다.
"""

from __future__ import annotations

import hashlib
import hmac

GOLDEN_HEX = "e4afb16c0e07eaf8ed219a072b59a47ae7619231c03cace98b376795901031e5"


def test_webhook_hmac_golden_vector_matches_fe_constant() -> None:
    """FE TestOrderDialog 가 동일 payload 로 계산하는 HMAC 과 byte-identical 해야 한다."""
    secret = b"test_secret_abc"
    body = (
        '{"symbol":"BTCUSDT",'
        '"side":"buy",'
        '"type":"market",'
        '"quantity":"0.001",'
        '"exchange_account_id":"550e8400-e29b-41d4-a716-446655440000"}'
    )
    expected = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
    assert expected == GOLDEN_HEX, (
        f"Golden vector drift detected — FE 와 BE 가 다른 hex 를 계산하면"
        f"webhook 서명이 거부된다. expected={GOLDEN_HEX}, got={expected}"
    )
