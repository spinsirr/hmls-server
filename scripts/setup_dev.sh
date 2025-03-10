#!/bin/bash

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create development database
echo "Setting up development database..."
createdb hmls || true
psql -d hmls -c "DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hmls') THEN
        CREATE USER hmls WITH PASSWORD 'hmls';
    END IF;
END
\$\$;"
psql -d hmls -c "GRANT ALL PRIVILEGES ON DATABASE hmls TO hmls;"
psql -d hmls -c "ALTER DATABASE hmls OWNER TO hmls;"
psql -d hmls -c "GRANT ALL ON SCHEMA public TO hmls;"

# Create test database
echo "Setting up test database..."
createdb hmls_test || true
psql -d hmls_test -c "DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hmls') THEN
        CREATE USER hmls WITH PASSWORD 'hmls';
    END IF;
END
\$\$;"
psql -d hmls_test -c "GRANT ALL PRIVILEGES ON DATABASE hmls_test TO hmls;"
psql -d hmls_test -c "ALTER DATABASE hmls_test OWNER TO hmls;"
psql -d hmls_test -c "GRANT ALL ON SCHEMA public TO hmls;"

# Set up Redis
echo "Setting up Redis..."
redis-cli CONFIG SET requirepass "hmls"
redis-cli AUTH hmls
redis-cli FLUSHALL

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    # Update the database URL and Redis URL
    sed -i '' 's|postgresql://username:password@localhost/dbname|postgresql://hmls:hmls@localhost/hmls|g' .env
    sed -i '' 's|redis://username:password@localhost:6379/0|redis://:hmls@localhost:6379/0|g' .env
fi

echo "Development environment setup complete!" 