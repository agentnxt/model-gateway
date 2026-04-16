#!/bin/bash
# postgres/init.sh
# Creates all application databases and users on first container start.
# Runs via /docker-entrypoint-initdb.d/ — once only on fresh volume.
set -e

echo "=== Initialising Autonomyx databases ==="

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" << EOSQL

DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'litellm') THEN
    CREATE USER litellm WITH PASSWORD '$LITELLM_DB_PASSWORD';
  END IF;
END \$\$;
CREATE DATABASE IF NOT EXISTS litellm;
ALTER DATABASE litellm OWNER TO litellm;
GRANT ALL PRIVILEGES ON DATABASE litellm TO litellm;

DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'langflow') THEN
    CREATE USER langflow WITH PASSWORD '$LANGFLOW_DB_PASSWORD';
  END IF;
END \$\$;
CREATE DATABASE IF NOT EXISTS langflow;
ALTER DATABASE langflow OWNER TO langflow;
GRANT ALL PRIVILEGES ON DATABASE langflow TO langflow;

DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'openfga') THEN
    CREATE USER openfga WITH PASSWORD '$OPENFGA_DB_PASSWORD';
  END IF;
END \$\$;
CREATE DATABASE IF NOT EXISTS openfga;
ALTER DATABASE openfga OWNER TO openfga;
GRANT ALL PRIVILEGES ON DATABASE openfga TO openfga;

DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'glitchtip') THEN
    CREATE USER glitchtip WITH PASSWORD '$GLITCHTIP_DB_PASSWORD';
  END IF;
END \$\$;
CREATE DATABASE IF NOT EXISTS glitchtip;
ALTER DATABASE glitchtip OWNER TO glitchtip;
GRANT ALL PRIVILEGES ON DATABASE glitchtip TO glitchtip;

EOSQL
echo "=== All databases and users created ==="

# Added by infisical setup
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'infisical') THEN
    CREATE USER infisical WITH PASSWORD '$INFISICAL_DB_PASSWORD';
  END IF;
END \$\$;
CREATE DATABASE IF NOT EXISTS infisical;
ALTER DATABASE infisical OWNER TO infisical;
GRANT ALL PRIVILEGES ON DATABASE infisical TO infisical;
