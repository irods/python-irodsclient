#!/bin/bash

# Adapted from "Initialization script" in documentation for official Postgres dockerhub:
#   https://hub.docker.com/_/postgres/
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE "ICAT";
    CREATE USER irods WITH PASSWORD 'testpassword';
    GRANT ALL PRIVILEGES ON DATABASE "ICAT" to irods;
EOSQL
