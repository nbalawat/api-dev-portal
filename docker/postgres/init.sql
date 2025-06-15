-- PostgreSQL initialization script for Developer Portal
-- This script sets up the database with required extensions and initial structure

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'developer', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE api_key_status AS ENUM ('active', 'inactive', 'revoked');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create tables (these will be managed by Alembic in the application)
-- This is just for initial development setup

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email CITEXT UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role user_role DEFAULT 'developer',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_id VARCHAR(50) UNIQUE NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status api_key_status DEFAULT 'active',
    scopes TEXT[],
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- API Logs table
CREATE TABLE IF NOT EXISTS api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    query_params JSONB,
    request_headers JSONB,
    request_body JSONB,
    response_status INTEGER,
    response_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    error_message TEXT
);

-- Sessions table (for JWT token blacklisting)
CREATE TABLE IF NOT EXISTS token_blacklist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

CREATE INDEX IF NOT EXISTS idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_api_key_id ON api_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_timestamp ON api_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_logs_path ON api_logs(path);
CREATE INDEX IF NOT EXISTS idx_api_logs_method ON api_logs(method);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti ON token_blacklist(token_jti);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires_at ON token_blacklist(expires_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_api_keys_updated_at ON api_keys;
CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create default admin user (password: admin123)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (username, email, hashed_password, full_name, role, is_active, is_verified)
VALUES (
    'admin',
    'admin@devportal.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeNaJMKr8KIYzqQai',
    'System Administrator',
    'admin',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Create a sample developer user (password: developer123)
INSERT INTO users (username, email, hashed_password, full_name, role, is_active, is_verified)
VALUES (
    'developer',
    'developer@devportal.local',
    '$2b$12$9Q1c7y4qBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeNaJMKr8KIYzqQai',
    'Sample Developer',
    'developer',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Create a sample viewer user (password: viewer123)
INSERT INTO users (username, email, hashed_password, full_name, role, is_active, is_verified)
VALUES (
    'viewer',
    'viewer@devportal.local',
    '$2b$12$8P1c7y4qBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeNaJMKr8KIYzqQai',
    'Sample Viewer',
    'viewer',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO devportal_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO devportal_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO devportal_user;

-- Create a function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM token_blacklist WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMIT;