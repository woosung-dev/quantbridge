"""Narrative 모듈 FastAPI 의존성 — `convert/dependencies.py` 와 같은 형태."""

from __future__ import annotations

from src.core.config import get_settings
from src.strategy.narrative.generate_service import GenerateService
from src.strategy.narrative.service import NarrativeService


def get_narrative_service() -> NarrativeService:
    return NarrativeService(get_settings())


def get_generate_service() -> GenerateService:
    return GenerateService(get_settings())
