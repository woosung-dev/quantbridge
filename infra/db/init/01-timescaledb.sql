-- TimescaleDB extension + 시계열 데이터용 별도 스키마 (컨테이너 최초 기동 시 1회 실행)
-- OHLCV hypertable 정의는 Alembic 마이그레이션에서 수행 (M2 T15)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 시계열 데이터용 격리 스키마 (일반 테이블과 분리, OHLCV hypertable 등 위치)
CREATE SCHEMA IF NOT EXISTS ts;
