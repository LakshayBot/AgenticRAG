-- Initialize database schema for .NET application

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS dotnet_app;

-- Set search path
SET search_path TO dotnet_app;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA dotnet_app TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dotnet_app TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dotnet_app TO postgres;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Note: Tables will be created by EF Core migrations
