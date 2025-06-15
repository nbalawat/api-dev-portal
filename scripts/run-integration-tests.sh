#!/bin/bash
set -e

# API Developer Portal - Integration Test Runner
# Runs comprehensive integration tests with database dependencies

echo "🧪 API Developer Portal - Integration Test Runner"
echo "=================================================="

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.test.yml"
TEST_CONTAINER="devportal_test_runner"
TEST_DB_CONTAINER="devportal_test_postgres"
TEST_REDIS_CONTAINER="devportal_test_redis"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up test environment..."
    cd "$PROJECT_ROOT"
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --volumes --remove-orphans >/dev/null 2>&1 || true
    docker container rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
    docker container rm -f "$TEST_DB_CONTAINER" >/dev/null 2>&1 || true
    docker container rm -f "$TEST_REDIS_CONTAINER" >/dev/null 2>&1 || true
    print_success "Cleanup completed"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    build       Build test environment
    run         Run integration tests
    full        Build and run integration tests
    auth        Run authentication tests only
    api         Run API integration tests only
    db          Run database integration tests only
    coverage    Run tests with coverage report
    watch       Run tests in watch mode
    clean       Clean up test environment
    help        Show this help message

Examples:
    $0 full                 # Build and run all integration tests
    $0 auth                 # Run authentication tests only
    $0 coverage             # Run tests with coverage report
    $0 clean                # Clean up test environment
EOF
}

# Function to build test environment
build_test_env() {
    print_status "Building integration test environment..."
    cd "$PROJECT_ROOT"
    
    # Build test images
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache test-suite
    
    print_success "Test environment built successfully"
}

# Function to start test services
start_test_services() {
    print_status "Starting test services..."
    cd "$PROJECT_ROOT"
    
    # Start test database and redis
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d test-postgres test-redis
    
    # Wait for services to be ready
    print_status "Waiting for test services to be ready..."
    sleep 10
    
    # Check if services are healthy
    for i in {1..30}; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "healthy"; then
            print_success "Test services are ready"
            return 0
        fi
        sleep 2
    done
    
    print_error "Test services failed to start properly"
    return 1
}

# Function to run integration tests
run_integration_tests() {
    local test_pattern="$1"
    local additional_args="$2"
    
    print_status "Running integration tests..."
    cd "$PROJECT_ROOT"
    
    # Start test services
    start_test_services
    
    # Run tests
    local test_cmd="python -m pytest tests/test_integration_*.py"
    
    if [[ -n "$test_pattern" ]]; then
        test_cmd="$test_cmd -k $test_pattern"
    fi
    
    if [[ -n "$additional_args" ]]; then
        test_cmd="$test_cmd $additional_args"
    fi
    
    print_status "Executing: $test_cmd"
    
    # Run tests in test container
    if docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm test-suite bash -c "$test_cmd"; then
        print_success "Integration tests completed successfully"
        return 0
    else
        print_error "Integration tests failed"
        return 1
    fi
}

# Function to run tests with coverage
run_tests_with_coverage() {
    print_status "Running integration tests with coverage..."
    
    local coverage_args="--cov=app --cov-report=html --cov-report=term-missing --cov-report=xml"
    
    if run_integration_tests "" "$coverage_args"; then
        print_success "Coverage report generated"
        
        # Show coverage summary
        echo ""
        print_status "Coverage Summary:"
        docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm test-suite bash -c "coverage report --show-missing"
        
        return 0
    else
        return 1
    fi
}

# Function to run tests in watch mode
run_watch_mode() {
    print_status "Running integration tests in watch mode..."
    print_warning "Press Ctrl+C to stop watching"
    
    # Start test services
    start_test_services
    
    # Run tests in watch mode
    docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm test-suite bash -c "
        pip install pytest-watch
        ptw tests/test_integration_*.py -- -v
    "
}

# Function to run specific test categories
run_auth_tests() {
    print_status "Running authentication integration tests..."
    run_integration_tests "auth" "-v"
}

run_api_tests() {
    print_status "Running API integration tests..."
    run_integration_tests "api" "-v"
}

run_db_tests() {
    print_status "Running database integration tests..."
    run_integration_tests "database" "-v"
}

# Main execution
main() {
    local command="${1:-help}"
    
    case "$command" in
        "build")
            build_test_env
            ;;
        "run")
            run_integration_tests
            ;;
        "full")
            build_test_env
            run_integration_tests
            ;;
        "auth")
            run_auth_tests
            ;;
        "api")
            run_api_tests
            ;;
        "db")
            run_db_tests
            ;;
        "coverage")
            run_tests_with_coverage
            ;;
        "watch")
            run_watch_mode
            ;;
        "clean")
            cleanup
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Execute main function
main "$@"