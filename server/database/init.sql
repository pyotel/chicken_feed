-- Create tables for chicken feeding monitoring system

-- Device configurations table
CREATE TABLE IF NOT EXISTS device_configs (
    device_id VARCHAR(100) PRIMARY KEY,
    feeding_times TEXT[] NOT NULL,
    duration_minutes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feeding logs table
CREATE TABLE IF NOT EXISTS feeding_logs (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Missed feedings table
CREATE TABLE IF NOT EXISTS missed_feedings (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    UNIQUE(device_id, scheduled_time)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_feeding_logs_device_action ON feeding_logs(device_id, action);
CREATE INDEX IF NOT EXISTS idx_feeding_logs_timestamp ON feeding_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_missed_feedings_device ON missed_feedings(device_id);
CREATE INDEX IF NOT EXISTS idx_missed_feedings_scheduled ON missed_feedings(scheduled_time);

-- Create view for daily statistics
CREATE OR REPLACE VIEW daily_feeding_stats AS
SELECT
    device_id,
    DATE(timestamp) as date,
    COUNT(CASE WHEN action = 'open' THEN 1 END) as total_opens,
    COUNT(CASE WHEN action = 'close' THEN 1 END) as total_closes,
    COUNT(CASE WHEN action = 'error' THEN 1 END) as total_errors,
    MIN(CASE WHEN action = 'open' THEN timestamp END) as first_feeding,
    MAX(CASE WHEN action = 'close' THEN timestamp END) as last_feeding
FROM feeding_logs
GROUP BY device_id, DATE(timestamp);