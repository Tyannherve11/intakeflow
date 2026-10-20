CREATE TABLE IF NOT EXISTS claims (
    id            SERIAL PRIMARY KEY,
    source_key    TEXT UNIQUE NOT NULL,
    claim_id      TEXT,
    employee_name TEXT,
    employee_id   TEXT,
    department    TEXT,
    claim_date    DATE,
    category      TEXT,
    amount        NUMERIC(10,2),
    description   TEXT,
    status        TEXT NOT NULL CHECK (status IN ('valid', 'rejected', 'duplicate')),
    issues        JSONB NOT NULL DEFAULT '[]',
    processed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         BIGSERIAL PRIMARY KEY,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_key TEXT NOT NULL,
    event      TEXT NOT NULL,
    detail     JSONB
);
