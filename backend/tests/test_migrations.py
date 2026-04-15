"""Alembic migration upgrade/downgrade round-trip 검증."""
from __future__ import annotations

import os

from alembic.config import Config

from alembic import command


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option(
        "sqlalchemy.url",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test",
        ).replace("+asyncpg", ""),  # alembic은 sync driver 필요
    )
    return cfg


def test_alembic_roundtrip(tmp_path, monkeypatch):
    """upgrade head → downgrade base → upgrade head가 모두 성공해야 함."""
    monkeypatch.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = _alembic_cfg()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
