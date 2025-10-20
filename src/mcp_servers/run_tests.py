#!/usr/bin/env python3
"""
Test runner for all MCP server tests
"""
import subprocess
import sys
import os

def run_all_tests():
    """Run all MCP server tests"""
    print("Running MCP Server Tests")
    print("=" * 50)
    
    # Run fitness knowledge tests
    print("\n1. Fitness Knowledge MCP Server Tests:")
    fitness_path = os.path.join(os.path.dirname(__file__), 'fitness_knowledge')
    result1 = subprocess.run([
        sys.executable, 'test_server.py'
    ], cwd=fitness_path, capture_output=True, text=True)
    
    if result1.returncode == 0:
        print("✓ Fitness Knowledge tests PASSED")
        try:
            test_count = result1.stdout.strip().split('Ran ')[1].split(' in ')[0]
            print(f"  {test_count} tests completed")
        except (IndexError, AttributeError):
            print("  Tests completed successfully")
    else:
        print("✗ Fitness Knowledge tests FAILED")
        print(result1.stderr)
    
    # Run spoonacular tests
    print("\n2. Spoonacular Enhanced MCP Server Tests:")
    spoonacular_path = os.path.join(os.path.dirname(__file__), 'spoonacular_enhanced')
    result2 = subprocess.run([
        sys.executable, 'test_server.py'
    ], cwd=spoonacular_path, capture_output=True, text=True)
    
    if result2.returncode == 0:
        print("✓ Spoonacular Enhanced tests PASSED")
        try:
            test_count = result2.stdout.strip().split('Ran ')[1].split(' in ')[0]
            print(f"  {test_count} tests completed")
        except (IndexError, AttributeError):
            print("  Tests completed successfully")
    else:
        print("✗ Spoonacular Enhanced tests FAILED")
        print(result2.stderr)
    
    # Summary
    print("\n" + "=" * 50)
    total_success = result1.returncode == 0 and result2.returncode == 0
    if total_success:
        print("🎉 All MCP server tests PASSED!")
    else:
        print("❌ Some tests FAILED. Check output above.")
    
    return total_success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)