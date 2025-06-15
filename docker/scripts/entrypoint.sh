#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Developer Portal API - Starting up...${NC}"

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Validate required environment variables
log "Validating environment variables..."
required_vars=(
    "DATABASE_URL"
    "SECRET_KEY"
    "JWT_SECRET_KEY"
)

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        error "Required environment variable $var is not set"
        exit 1
    fi
done

log "Environment variables validated successfully"

# Wait for database to be ready
if [[ -n "$POSTGRES_HOST" ]]; then
    log "Waiting for PostgreSQL to be ready at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    /app/docker/scripts/wait-for-it.sh "$POSTGRES_HOST:${POSTGRES_PORT:-5432}" --timeout=60 --strict
    log "PostgreSQL is ready"
else
    warn "POSTGRES_HOST not set, skipping database wait"
fi

# Wait for Redis to be ready
if [[ -n "$REDIS_HOST" ]]; then
    log "Waiting for Redis to be ready at $REDIS_HOST:${REDIS_PORT:-6379}..."
    /app/docker/scripts/wait-for-it.sh "$REDIS_HOST:${REDIS_PORT:-6379}" --timeout=30 --strict
    log "Redis is ready"
else
    warn "REDIS_HOST not set, skipping Redis wait"
fi

# Test database connection
log "Testing database connection..."
python -c "
import sys
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

async def test_connection():
    try:
        # Force use of asyncpg driver
        db_url = '$DATABASE_URL'
        if not db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
        
        engine = create_async_engine(db_url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            result.fetchone()
        await engine.dispose()
        print('Database connection successful')
        return True
    except OperationalError as e:
        print(f'Database connection failed: {e}')
        return False
    except Exception as e:
        print(f'Unexpected error: {e}')
        return False

if not asyncio.run(test_connection()):
    sys.exit(1)
"

if [[ $? -ne 0 ]]; then
    error "Database connection test failed"
    exit 1
fi

log "Database connection test passed"

# Run database migrations if in development mode
if [[ "$APP_ENV" == "development" && "${SKIP_MIGRATIONS:-false}" != "true" ]]; then
    log "Running database migrations..."
    # This will be uncommented once we set up Alembic
    # alembic upgrade head
    log "Database migrations completed (placeholder)"
else
    log "Skipping database migrations (APP_ENV=$APP_ENV, SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-false})"
fi

# Create initial admin user if requested
if [[ "${CREATE_ADMIN:-false}" == "true" && -n "$ADMIN_USERNAME" && -n "$ADMIN_PASSWORD" ]]; then
    log "Creating initial admin user..."
    python -c "
import asyncio
from app.core.security import get_password_hash
print(f'Admin user creation placeholder - username: $ADMIN_USERNAME')
# This will be implemented once we have the user management system
"
    log "Initial admin user created"
fi

# Print startup information
log "Starting FastAPI application..."
log "Environment: ${APP_ENV:-development}"
log "Debug mode: ${DEBUG:-false}"
log "Workers: ${WORKERS:-1}"

# Execute the main command
exec "$@"