-- Initial schema for calendar PostgreSQL repository
-- This creates the tables needed for calendar events, schedules, and sync state

-- Calendar events table with rich querying support
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    calendar_id VARCHAR(255) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    organizer VARCHAR(255),
    attendee_count INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL,
    event_data JSONB NOT NULL,
    last_modified TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint for calendar_id + event_id
    CONSTRAINT unique_calendar_event UNIQUE (calendar_id, event_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_calendar_events_calendar_id ON calendar_events(calendar_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_end_time ON calendar_events(end_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_time_range ON calendar_events(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_organizer ON calendar_events(organizer);
CREATE INDEX IF NOT EXISTS idx_calendar_events_status ON calendar_events(status);
CREATE INDEX IF NOT EXISTS idx_calendar_events_attendee_count ON calendar_events(attendee_count);

-- GIN index for JSONB event_data for rich querying
CREATE INDEX IF NOT EXISTS idx_calendar_events_data ON calendar_events USING GIN (event_data);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    id SERIAL PRIMARY KEY,
    schedule_id VARCHAR(255) NOT NULL UNIQUE,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL,
    schedule_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_updated_at TIMESTAMPTZ NOT NULL
);

-- Indexes for schedules
CREATE INDEX IF NOT EXISTS idx_schedules_start_date ON schedules(start_date);
CREATE INDEX IF NOT EXISTS idx_schedules_end_date ON schedules(end_date);
CREATE INDEX IF NOT EXISTS idx_schedules_status ON schedules(status);
CREATE INDEX IF NOT EXISTS idx_schedules_date_range ON schedules(start_date, end_date);

-- Calendar sync state table for managing incremental sync
CREATE TABLE IF NOT EXISTS calendar_sync_state (
    id SERIAL PRIMARY KEY,
    source_calendar_id VARCHAR(255) NOT NULL UNIQUE,
    sync_token TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Index for sync state lookups
CREATE INDEX IF NOT EXISTS idx_sync_state_calendar_id ON calendar_sync_state(source_calendar_id);

-- Update triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_calendar_events_updated_at 
    BEFORE UPDATE ON calendar_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schedules_updated_at 
    BEFORE UPDATE ON schedules 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
