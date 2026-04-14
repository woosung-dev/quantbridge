-- TimescaleDB extension 활성화 (컨테이너 최초 기동 시 1회 실행)
-- OHLCV hypertable 정의는 Alembic 마이그레이션에서 수행 (Session 2 backend)
CREATE EXTENSION IF NOT EXISTS timescaledb;
