#!/bin/bash

# Drop the test database if it exists
dropdb hmls_test || true

# Create the test database
createdb hmls_test

# Create the test user if it doesn't exist
psql -d hmls_test -c "DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hmls') THEN
        CREATE USER hmls WITH PASSWORD 'hmls';
    END IF;
END
\$\$;"

# Grant privileges to the test user
psql -d hmls_test -c "GRANT ALL PRIVILEGES ON DATABASE hmls_test TO hmls;"
psql -d hmls_test -c "ALTER DATABASE hmls_test OWNER TO hmls;"
psql -d hmls_test -c "GRANT ALL ON SCHEMA public TO hmls;" 