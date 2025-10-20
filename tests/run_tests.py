#!/usr/bin/env python3
"""
Test runner for fitness coach comprehensive testing suite
Task 8: Implement comprehensive testing suite

This script runs integration tests and performance tests for the fitness coach system.
It provides options to run different test categories and generates test reports.
"""

import os
import sys
import subprocess
import argparse
import time
from datetime import datetime


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=True
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ {description} completed successfully in {duration:.2f}s")
        
        if result.stdout:
            print("\nOutput:")
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ {description} failed after {duration:.2f}s")
        print(f"Exit code: {e.returncode}")
        
        if e.stdout:
            print("\nStdout:")
            print(e.stdout)
        
        if e.stderr:
            print("\nStderr:")
            print(e.stderr)
        
        return False


def install_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    
    dependencies = [
        'pytest>=7.0.0',
        'pytest-asyncio>=0.21.0',
        'pytest-cov>=4.0.0',
        'pytest-html>=3.1.0',
        'pytest-xdist>=3.0.0',
        'moto[dynamodb,lambda,bedrock]>=4.2.0',
        'boto3>=1.26.0',
        'botocore>=1.29.0'
    ]
    
    for dep in dependencies:
        command = [sys.executable, '-m', 'pip', 'install', dep]
        if not run_command(command, f"Installing {dep}"):
            return False
    
    return True


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests"""
    command = [sys.executable, '-m', 'pytest']
    
    # Add test markers
    command.extend(['-m', 'unit'])
    
    # Add verbosity
    if verbose:
        command.append('-v')
    
    # Add coverage
    if coverage:
        command.extend(['--cov=../src', '--cov-report=html', '--cov-report=term'])
    
    # Add test discovery
    command.extend(['../src', '--tb=short'])
    
    return run_command(command, "Unit Tests")


def run_integration_tests(verbose=False, parallel=False):
    """Run integration tests"""
    command = [sys.executable, '-m', 'pytest']
    
    # Add test file
    command.append('integration/test_full_workflow.py')
    
    # Add markers
    command.extend(['-m', 'integration'])
    
    # Add verbosity
    if verbose:
        command.append('-v')
    
    # Add parallel execution
    if parallel:
        command.extend(['-n', 'auto'])
    
    # Add HTML report
    command.extend(['--html=reports/integration_report.html', '--self-contained-html'])
    
    # Add other options
    command.extend(['--tb=short', '--strict-markers'])
    
    return run_command(command, "Integration Tests")


def run_performance_tests(verbose=False):
    """Run performance tests"""
    command = [sys.executable, '-m', 'pytest']
    
    # Add test file
    command.append('performance/test_load_performance.py')
    
    # Add markers
    command.extend(['-m', 'performance'])
    
    # Add verbosity
    if verbose:
        command.append('-v')
    
    # Add HTML report
    command.extend(['--html=reports/performance_report.html', '--self-contained-html'])
    
    # Add other options
    command.extend(['--tb=short', '--strict-markers'])
    
    return run_command(command, "Performance Tests")


def run_all_tests(verbose=False, coverage=False, parallel=False):
    """Run all test categories"""
    print(f"\n🚀 Starting comprehensive test suite at {datetime.now()}")
    
    results = {
        'unit': False,
        'integration': False,
        'performance': False
    }
    
    # Create reports directory
    os.makedirs('reports', exist_ok=True)
    
    # Run unit tests
    print("\n📋 Running Unit Tests...")
    results['unit'] = run_unit_tests(verbose=verbose, coverage=coverage)
    
    # Run integration tests
    print("\n🔗 Running Integration Tests...")
    results['integration'] = run_integration_tests(verbose=verbose, parallel=parallel)
    
    # Run performance tests
    print("\n⚡ Running Performance Tests...")
    results['performance'] = run_performance_tests(verbose=verbose)
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUITE SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_type, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_type.upper():15} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} test categories passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed successfully!")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(
        description="Fitness Coach Comprehensive Testing Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --all                    # Run all tests
  python run_tests.py --integration            # Run only integration tests
  python run_tests.py --performance            # Run only performance tests
  python run_tests.py --unit --coverage        # Run unit tests with coverage
  python run_tests.py --all --verbose          # Run all tests with verbose output
        """
    )
    
    # Test category options
    parser.add_argument('--all', action='store_true', help='Run all test categories')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    
    # Test options
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--install-deps', action='store_true', help='Install test dependencies')
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            return 1
    
    # Determine which tests to run
    if not any([args.all, args.unit, args.integration, args.performance]):
        print("No test category specified. Use --help for options.")
        return 1
    
    success = True
    
    if args.all:
        success = run_all_tests(
            verbose=args.verbose,
            coverage=args.coverage,
            parallel=args.parallel
        )
    else:
        # Create reports directory
        os.makedirs('reports', exist_ok=True)
        
        if args.unit:
            success &= run_unit_tests(verbose=args.verbose, coverage=args.coverage)
        
        if args.integration:
            success &= run_integration_tests(verbose=args.verbose, parallel=args.parallel)
        
        if args.performance:
            success &= run_performance_tests(verbose=args.verbose)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())