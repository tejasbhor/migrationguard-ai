-- Initialize MigrationGuard AI database with TimescaleDB extension

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create schema for application
CREATE SCHEMA IF NOT EXISTS migrationguard;

-- Set search path
SET search_path TO migrationguard, public;

-- Grant privileges
GRANT ALL PRIVILEGES ON SCHEMA migrationguard TO migrationguard;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA migrationguard TO migrationguard;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA migrationguard TO migrationguard;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'MigrationGuard AI database initialized successfully';
END $$;
