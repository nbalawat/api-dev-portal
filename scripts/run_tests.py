#!/usr/bin/env python3
"""
Test Runner for API Key Management System

This script runs all tests for the API key management system and provides
a summary of results.
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_pattern=None, verbose=False, coverage=False):
    """Run tests with optional pattern filtering."""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd.append("tests/")
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Add test pattern if provided
    if test_pattern:
        cmd.extend(["-k", test_pattern])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--color=yes",
        "--durations=10"
    ])
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main function for test runner."""
    parser = argparse.ArgumentParser(
        description="Run tests for API Key Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                          # Run all tests
  python run_tests.py -v                       # Run with verbose output
  python run_tests.py -c                       # Run with coverage
  python run_tests.py -k "test_api_key"        # Run tests matching pattern
  python run_tests.py -k "not slow"            # Skip slow tests
        """
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    parser.add_argument(
        "-k", "--keyword",
        help="Only run tests matching given substring expression"
    )
    
    parser.add_argument(
        "--unit",
        action="store_const",
        const="unit",
        dest="test_type",
        help="Run only unit tests"
    )
    
    parser.add_argument(
        "--integration",
        action="store_const",
        const="integration",
        dest="test_type",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "--security",
        action="store_const",
        const="security",
        dest="test_type",
        help="Run only security-related tests"
    )
    
    args = parser.parse_args()
    
    # Build test pattern from arguments
    test_pattern = args.keyword
    if args.test_type:
        if test_pattern:
            test_pattern = f"{test_pattern} and {args.test_type}"
        else:
            test_pattern = args.test_type
    
    # Check if tests directory exists
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("Error: tests/ directory not found")
        print("Make sure you're running this from the project root directory")
        return 1
    
    # Run tests
    print("🚀 Starting API Key Management System Tests")
    print(f"📁 Test directory: {tests_dir.absolute()}")
    
    if test_pattern:
        print(f"🔍 Test pattern: {test_pattern}")
    
    if args.coverage:
        print("📊 Coverage reporting enabled")
    
    print()
    
    exit_code = run_tests(
        test_pattern=test_pattern,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    print()
    
    if exit_code == 0:
        print("✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print("❌ Some tests failed!")
    
    print()
    print("💡 Tips:")
    print("  - Use -v for verbose output")
    print("  - Use -c for coverage reporting")
    print('  - Use -k "pattern" to run specific tests')
    print('  - Use -k "not slow" to skip slow tests')
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())