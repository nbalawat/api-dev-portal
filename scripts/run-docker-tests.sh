#!/bin/bash
# Comprehensive Docker Test Runner Script
# Provides multiple testing scenarios with proper cleanup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
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

# Function to cleanup test containers
cleanup() {
    print_status "🧹 Cleaning up test containers..."
    docker-compose -f docker-compose.test.yml down --volumes --remove-orphans 2>/dev/null || true
    print_success "Cleanup completed"
}

# Function to run specific test type
run_test_type() {
    local test_type=$1
    local service_name=$2
    
    print_status "🧪 Running ${test_type} tests..."
    
    if docker-compose -f docker-compose.test.yml run --rm ${service_name}; then
        print_success "${test_type} tests passed!"
        return 0
    else
        print_error "${test_type} tests failed!"
        return 1
    fi
}

# Function to generate test report
generate_report() {
    print_status "📊 Generating test reports..."
    
    # Create reports directory if it doesn't exist
    mkdir -p ./test-results
    
    # Copy reports from volume if available
    docker run --rm \
        -v api-developer-portal_test-reports:/source \
        -v "$(pwd)/test-results":/dest \
        busybox sh -c "cp -r /source/* /dest/ 2>/dev/null || echo 'No reports found'" || true
    
    if [ -d "./test-results/coverage" ]; then
        print_success "Coverage report generated: ./test-results/coverage/index.html"
    fi
    
    if [ -f "./test-results/junit.xml" ]; then
        print_success "JUnit report generated: ./test-results/junit.xml"
    fi
}

# Function to show usage
show_usage() {
    echo "🧪 Docker Test Runner for API Developer Portal"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all               Run all tests (default)"
    echo "  unit              Run unit tests only (fast)"
    echo "  integration       Run integration tests with database"
    echo "  api               Run API endpoint tests"
    echo "  build             Build test image only"
    echo "  clean             Clean up test containers and volumes"
    echo "  report            Generate test reports"
    echo "  coverage          Run tests with coverage report"
    echo "  watch             Run tests in watch mode (for development)"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Run all tests"
    echo "  $0 unit           # Run only unit tests"
    echo "  $0 coverage       # Run tests with coverage"
    echo "  $0 clean          # Clean up everything"
}

# Main execution logic
main() {
    local command=${1:-all}
    
    case $command in
        "help"|"--help"|"-h")
            show_usage
            exit 0
            ;;
        "clean")
            cleanup
            exit 0
            ;;
        "build")
            print_status "🏗️  Building test image..."
            docker build --target test -t api-portal-test .
            print_success "Test image built successfully"
            exit 0
            ;;
        "unit")
            print_status "🚀 Starting unit tests..."
            cleanup
            run_test_type "Unit" "unit-tests"
            cleanup
            ;;
        "integration")
            print_status "🚀 Starting integration tests..."
            cleanup
            run_test_type "Integration" "integration-tests"
            cleanup
            ;;
        "api")
            print_status "🚀 Starting API tests..."
            cleanup
            print_status "📡 Starting test application..."
            docker-compose -f docker-compose.test.yml up -d test-postgres test-redis test-app
            
            # Wait for services to be ready
            print_status "⏳ Waiting for services to be ready..."
            sleep 15
            
            run_test_type "API" "api-tests"
            cleanup
            ;;
        "coverage")
            print_status "🚀 Starting tests with coverage..."
            cleanup
            run_test_type "Coverage" "test-suite"
            generate_report
            cleanup
            ;;
        "report")
            generate_report
            ;;
        "watch")
            print_status "🚀 Starting tests in watch mode..."
            print_warning "Press Ctrl+C to stop watching"
            cleanup
            
            # Start test infrastructure
            docker-compose -f docker-compose.test.yml up -d test-postgres test-redis
            
            # Run tests in watch mode
            docker-compose -f docker-compose.test.yml run --rm \
                -v "$(pwd)/tests:/app/tests" \
                -v "$(pwd)/app:/app/app" \
                test-suite \
                sh -c "pip install pytest-watch && ptw tests/ app/ --runner 'python -m pytest tests/ -v'"
            
            cleanup
            ;;
        "all"|"")
            print_status "🚀 Starting comprehensive test suite..."
            cleanup
            
            # Build test image first
            print_status "🏗️  Building test image..."
            docker build --target test -t api-portal-test .
            
            local exit_code=0
            
            # Run unit tests
            if ! run_test_type "Unit" "unit-tests"; then
                exit_code=1
            fi
            
            # Run integration tests
            if ! run_test_type "Integration" "integration-tests"; then
                exit_code=1
            fi
            
            # Run full test suite with coverage
            if ! run_test_type "Full Suite" "test-suite"; then
                exit_code=1
            fi
            
            # Generate reports
            generate_report
            
            cleanup
            
            if [ $exit_code -eq 0 ]; then
                print_success "🎉 All tests passed!"
            else
                print_error "❌ Some tests failed!"
            fi
            
            exit $exit_code
            ;;
        *)
            print_error "Unknown option: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Trap to ensure cleanup on script exit
trap cleanup EXIT

# Run main function
main "$@"