# Convert 모듈 FastAPI 의존성
from __future__ import annotations

from src.core.config import get_settings
from src.strategy.convert.service import ConvertService


def get_convert_service() -> ConvertService:
    return ConvertService(get_settings())
