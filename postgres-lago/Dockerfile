# Lago's structure.sql requires the pg_partman extension, which isn't in
# postgres:15-alpine. Extend the Debian variant which has it in apt.
FROM postgres:15.7-bullseye

RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-15-partman \
 && rm -rf /var/lib/apt/lists/*
