-- Setup script: Provisions the 'firms' database and required extensions/plugins.
-- This script is executed against the PostgreSQL server maintenance catalog (postgres).

-- 1. Ensure 'firms' database exists
SELECT 'CREATE DATABASE firms'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'firms')\gexec

-- 2. Connect to the firms database
\connect firms

-- 3. Ensure required plugins/extensions are installed
CREATE EXTENSION IF NOT EXISTS postgis;
