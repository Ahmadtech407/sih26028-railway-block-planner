-- ==============================================================================
-- Indian Railways AI Section Controller & Block Planner (SIH26028)
-- Supabase PostgreSQL Master Database Schema
-- ==============================================================================

-- 1. Users & Passenger Authentication
CREATE TABLE IF NOT EXISTS public.users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    identifier TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
);

-- 2. Railway Stations Master Catalog
CREATE TABLE IF NOT EXISTS public.stations (
    id BIGSERIAL PRIMARY KEY,
    station_code TEXT UNIQUE NOT NULL,
    station_name TEXT NOT NULL,
    city TEXT,
    state TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Operational Trains Master Catalog
CREATE TABLE IF NOT EXISTS public.trains (
    id BIGSERIAL PRIMARY KEY,
    train_number TEXT UNIQUE NOT NULL,
    train_name TEXT NOT NULL,
    train_type TEXT DEFAULT 'EXPRESS',
    source_code TEXT,
    dest_code TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Train Route Sequences & Platform Timings
CREATE TABLE IF NOT EXISTS public.train_routes (
    id BIGSERIAL PRIMARY KEY,
    train_id BIGINT REFERENCES public.trains(id) ON DELETE CASCADE,
    station_id BIGINT REFERENCES public.stations(id) ON DELETE CASCADE,
    sequence_order INT NOT NULL,
    scheduled_arrival TEXT,
    scheduled_departure TEXT,
    platform_number TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Daily Train Schedules & Delay Tracking
CREATE TABLE IF NOT EXISTS public.train_schedules (
    id BIGSERIAL PRIMARY KEY,
    train_id BIGINT REFERENCES public.trains(id) ON DELETE CASCADE,
    journey_date DATE DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'SCHEDULED',
    delay_minutes INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Live Telemetry & Kinematic Positions
CREATE TABLE IF NOT EXISTS public.train_live_positions (
    id BIGSERIAL PRIMARY KEY,
    train_number TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    speed_kmph NUMERIC DEFAULT 0,
    current_station TEXT,
    next_station TEXT,
    delay_minutes INT DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Platform Status & Occupancy
CREATE TABLE IF NOT EXISTS public.platform_status (
    id BIGSERIAL PRIMARY KEY,
    station_code TEXT NOT NULL,
    platform_number TEXT NOT NULL,
    is_occupied BOOLEAN DEFAULT FALSE,
    occupying_train TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(station_code, platform_number)
);

-- 8. Machine Learning Congestion & Delay Predictions
CREATE TABLE IF NOT EXISTS public.ml_predictions (
    id BIGSERIAL PRIMARY KEY,
    train_number TEXT,
    section_id TEXT,
    predicted_delay_min NUMERIC DEFAULT 0,
    congestion_score NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Meteorological Station Observations
CREATE TABLE IF NOT EXISTS public.weather_data (
    id BIGSERIAL PRIMARY KEY,
    station_code TEXT,
    temperature_c NUMERIC,
    condition TEXT,
    rain_prob_pct NUMERIC,
    observed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Track Section Congestion Indices
CREATE TABLE IF NOT EXISTS public.congestion_data (
    id BIGSERIAL PRIMARY KEY,
    section_id TEXT,
    congestion_level TEXT DEFAULT 'LOW',
    train_count INT DEFAULT 0,
    observed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for high-frequency queries
CREATE INDEX IF NOT EXISTS idx_users_identifier ON public.users(identifier);
CREATE INDEX IF NOT EXISTS idx_stations_code ON public.stations(station_code);
CREATE INDEX IF NOT EXISTS idx_trains_number ON public.trains(train_number);
CREATE INDEX IF NOT EXISTS idx_train_live_train_no ON public.train_live_positions(train_number);
CREATE INDEX IF NOT EXISTS idx_platform_stn ON public.platform_status(station_code);
