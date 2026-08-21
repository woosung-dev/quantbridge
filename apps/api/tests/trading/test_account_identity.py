# 거래소 계정 행을 실제 계정 단위로 고르는 순수 판정 계약을 고정한다.
"""account_identity 모듈의 exchange_uid 대표 행 선택 회귀 테스트."""

from __future__ import annotations

from types import SimpleNamespace

from src.trading.account_identity import dedupe_accounts_by_exchange_uid


def _account(
    exchange_uid: str | None,
    read_only: bool | None,
    label: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        exchange_uid=exchange_uid,
        read_only=read_only,
        label=label,
    )


def test_same_exchange_uid_keeps_one_row() -> None:
    """같은 exchange_uid의 두 행은 대표 하나만 남긴다."""
    first = _account("uid-a", False, "first")
    duplicate = _account("uid-a", False, "duplicate")

    result = dedupe_accounts_by_exchange_uid([first, duplicate])

    assert result == [first]
    assert result[0] is first


def test_none_exchange_uid_rows_are_never_grouped() -> None:
    """실체가 미상인 None uid 행은 서로 다른 계정일 수 있어 모두 보존한다."""
    unknowns = [
        _account(None, False, "first"),
        _account(None, True, "second"),
        _account(None, None, "third"),
    ]

    result = dedupe_accounts_by_exchange_uid(unknowns)

    assert result == unknowns
    assert all(actual is expected for actual, expected in zip(result, unknowns, strict=True))


def test_writable_row_replaces_read_only_representative() -> None:
    """같은 uid에서는 앞선 read_only 행보다 뒤의 writable 행이 대표다."""
    read_only = _account("uid-a", True, "read-only")
    writable = _account("uid-a", False, "writable")

    result = dedupe_accounts_by_exchange_uid([read_only, writable])

    assert result == [writable]
    assert result[0] is writable


def test_first_writable_row_wins_when_both_rows_are_writable() -> None:
    """동일 uid의 writable 행끼리는 호출부가 준 입력 순서를 보존한다."""
    first = _account("uid-a", False, "first")
    later = _account("uid-a", False, "later")

    result = dedupe_accounts_by_exchange_uid([first, later])

    assert result == [first]
    assert result[0] is first


def test_replacement_keeps_first_uid_position_in_output() -> None:
    """뒤 행이 A 대표로 교체돼도 출력에서 A의 처음 등장 위치는 유지한다."""
    first_a = _account("uid-a", True, "first-a")
    only_b = _account("uid-b", False, "only-b")
    writable_a = _account("uid-a", False, "writable-a")

    result = dedupe_accounts_by_exchange_uid([first_a, only_b, writable_a])

    assert [account.exchange_uid for account in result] == ["uid-a", "uid-b"]
    assert result[0] is writable_a
    assert result[1] is only_b


def test_none_read_only_replaces_read_only_representative() -> None:
    """관측값: read_only=None은 True가 아닌 값이라 writable 대표 후보로 취급한다."""
    read_only = _account("uid-a", True, "read-only")
    unspecified = _account("uid-a", None, "unspecified")

    result = dedupe_accounts_by_exchange_uid([read_only, unspecified])

    assert result == [unspecified]
    assert result[0] is unspecified


def test_empty_list_returns_empty_list() -> None:
    """빈 입력은 빈 출력이다."""
    assert dedupe_accounts_by_exchange_uid([]) == []


def test_unique_accounts_preserve_identity_and_order() -> None:
    """양성 대조: 중복이 없으면 길이·순서·원소 동일성이 모두 유지된다."""
    accounts = [
        _account("uid-a", False, "a"),
        _account(None, True, "unknown"),
        _account("uid-b", True, "b"),
    ]

    result = dedupe_accounts_by_exchange_uid(accounts)

    assert len(result) == len(accounts)
    assert all(actual is expected for actual, expected in zip(result, accounts, strict=True))
