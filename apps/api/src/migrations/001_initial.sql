CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS watches (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    aoi GEOMETRY(POLYGON, 4326) NOT NULL,
    sensor_preference VARCHAR(50) NOT NULL DEFAULT 'auto',
    frequency VARCHAR(50) NOT NULL DEFAULT 'once',
    alert_threshold TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS watches_aoi_idx ON watches USING GIST(aoi);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR PRIMARY KEY,
    watch_id VARCHAR NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
    skyfi_order_id VARCHAR,
    skyfi_archive_id VARCHAR,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    sensor_type VARCHAR(100) NOT NULL,
    analytics_type VARCHAR(100),
    cost_usd FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    answer TEXT,
    confidence VARCHAR(20),
    evidence JSONB,
    raw_analytics JSONB,
    imagery_url TEXT,
    captured_at TIMESTAMP,
    agent_thoughts JSONB
);

CREATE INDEX IF NOT EXISTS orders_watch_id_idx ON orders(watch_id);
CREATE INDEX IF NOT EXISTS orders_status_idx ON orders(status);
CREATE INDEX IF NOT EXISTS orders_skyfi_order_id_idx ON orders(skyfi_order_id);
