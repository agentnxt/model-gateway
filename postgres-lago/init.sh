#!/bin/bash
# postgres-lago/init.sh — runs via /docker-entrypoint-initdb.d/ on first start.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lago') THEN
      CREATE USER lago WITH PASSWORD '${LAGO_DB_PASSWORD}';
    END IF;
  END \$\$;
  SELECT 'CREATE DATABASE lago' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lago')\gexec
  ALTER DATABASE lago OWNER TO lago;
  GRANT ALL PRIVILEGES ON DATABASE lago TO lago;
EOSQL

# Fix public-schema ownership (Postgres 15+) and pre-create the partman schema.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname lago <<-EOSQL
  GRANT ALL ON SCHEMA public TO lago;
  ALTER SCHEMA public OWNER TO lago;
  CREATE SCHEMA IF NOT EXISTS partman AUTHORIZATION lago;
EOSQL
