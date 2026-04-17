#!/bin/bash
# postgres/init.sh
# Creates all application databases and users on first container start.
# Runs via /docker-entrypoint-initdb.d/ — once only on fresh volume.
# Idempotent: uses \gexec because Postgres has no CREATE DATABASE IF NOT EXISTS.
#
# Postgres 15+ changed public-schema defaults: only the DB-creator role (here,
# the superuser POSTGRES_USER) owns the public schema of a freshly-created DB,
# so app users couldn't CREATE on public. We reassign `public` ownership to
# each app user so Prisma / Rails / Django migrations can run.
set -e

echo "=== Initialising Autonomyx databases ==="

provision_db() {
  local user="$1"
  local password="$2"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$ BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${user}') THEN
        CREATE USER ${user} WITH PASSWORD '${password}';
      END IF;
    END \$\$;
    SELECT 'CREATE DATABASE ${user}'
      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${user}')\gexec
    ALTER DATABASE ${user} OWNER TO ${user};
    GRANT ALL PRIVILEGES ON DATABASE ${user} TO ${user};
EOSQL
  # Fix public-schema ownership (Postgres 15+).
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${user}" <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${user};
    ALTER SCHEMA public OWNER TO ${user};
EOSQL
}

provision_db litellm    "$LITELLM_DB_PASSWORD"
provision_db langflow   "$LANGFLOW_DB_PASSWORD"
provision_db openfga    "$OPENFGA_DB_PASSWORD"
provision_db glitchtip  "$GLITCHTIP_DB_PASSWORD"
provision_db infisical  "$INFISICAL_DB_PASSWORD"
provision_db lago       "$LAGO_DB_PASSWORD"
provision_db langfuse   "$LANGFUSE_DB_PASSWORD"

echo "=== All databases and users created ==="
