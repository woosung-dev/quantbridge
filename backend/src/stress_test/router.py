"""stress_test HTTP 라우터. 실제 엔드포인트는 Stage 3에서 구현."""

from fastapi import APIRouter

router = APIRouter(prefix="/stress-test", tags=["stress_test"])
