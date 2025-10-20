#!/usr/bin/env python3
"""
Test MCP Server Deployment

Simple test script to validate MCP server functionality without encoding issues.
"""

import asyncio
import sys
import time
from pathlib import Path

async def test_fitness_server():
    """Test Fitness Knowledge MCP Server"""
    print("Testing Fitness Knowledge MCP Server...")
    
    try:
        # Add server path to Python path
        server_path = Path("src/mcp_servers/fitness_knowledge")
        sys.path.insert(0, str(server_path))
        
        from server import FitnessKnowledgeMCPServer
        
        server = FitnessKnowledgeMCPServer()
        
        # Test basic functionality
        start_time = time.time()
        
        # Test exercise info
        exercise_info = await server.get_exercise_info("push_up")
        assert "name" in exercise_info, "Exercise info should contain name"
        
        # Test workout progression
        progression = await server.suggest_workout_progression(
            {"exercises": ["push_up", "squat"]}, "beginner"
        )
        assert "progression_recommendations" in progression, "Should have progression recommendations"
        
        # Test workout balance
        balance = await server.validate_workout_balance({
            "exercises": ["push_up", "pull_up", "squat"]
        })
        assert "balanced" in balance, "Should have balance assessment"
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"SUCCESS: Fitness server test completed in {response_time:.3f} seconds")
        return True
        
    except Exception as e:
        print(f"FAILED: Fitness server test failed: {e}")
        return False

async def test_spoonacular_server():
    """Test Spoonacular Enhanced MCP Server"""
    print("Testing Spoonacular Enhanced MCP Server...")
    
    try:
        # Clear any previous imports and add correct path
        if 'server' in sys.modules:
            del sys.modules['server']
        
        # Add server path to Python path
        server_path = Path("src/mcp_servers/spoonacular_enhanced")
        sys.path.insert(0, str(server_path))
        
        from server import SpoonacularEnhancedMCPServer
        
        server = SpoonacularEnhancedMCPServer()
        
        # Test basic functionality
        start_time = time.time()
        
        # Test meal plan generation
        meal_plan = await server.get_optimized_meal_plan(
            dietary_preferences=["omnivore"],
            calorie_target=2000,
            fitness_goals="maintenance",
            days=3
        )
        assert "meal_plan" in meal_plan, "Should have meal plan"
        
        # Test nutrition analysis
        analysis = await server.analyze_nutrition_balance(meal_plan["meal_plan"])
        assert "analysis_summary" in analysis, "Should have analysis summary"
        
        # Test recipe suggestions
        recipes = await server.get_recipe_suggestions(
            calorie_range=(300, 500),
            dietary_preferences=["vegetarian"]
        )
        assert "recipes" in recipes, "Should have recipe suggestions"
        
        end_time = time.time()
        response_time = end_time - start_time
        
        await server.close()
        
        print(f"SUCCESS: Spoonacular server test completed in {response_time:.3f} seconds")
        return True
        
    except Exception as e:
        print(f"FAILED: Spoonacular server test failed: {e}")
        return False

async def create_lambda_config():
    """Create Lambda configuration for MCP servers"""
    print("Creating Lambda MCP server configuration...")
    
    try:
        import json
        
        # Create Lambda environment configuration
        lambda_config = {
            "MCP_SERVERS": {
                "fitness_knowledge": {
                    "endpoint": "http://localhost:8001",
                    "health_check": "/health",
                    "timeout": 30
                },
                "spoonacular_enhanced": {
                    "endpoint": "http://localhost:8002", 
                    "health_check": "/health",
                    "timeout": 30
                }
            }
        }
        
        # Save configuration for Lambda functions
        config_dir = Path("src/lambda/config")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / "mcp_servers.json"
        with open(config_file, 'w') as f:
            json.dump(lambda_config, f, indent=2)
        
        print(f"SUCCESS: Lambda MCP config created at {config_file}")
        return True
        
    except Exception as e:
        print(f"FAILED: Lambda configuration failed: {e}")
        return False

async def main():
    """Main test function"""
    print("MCP Server Deployment Test Starting...")
    print("=" * 50)
    
    results = []
    
    # Test Fitness Knowledge Server
    fitness_result = await test_fitness_server()
    results.append(("Fitness Knowledge Server", fitness_result))
    
    print()
    
    # Test Spoonacular Enhanced Server
    spoonacular_result = await test_spoonacular_server()
    results.append(("Spoonacular Enhanced Server", spoonacular_result))
    
    print()
    
    # Create Lambda configuration
    lambda_result = await create_lambda_config()
    results.append(("Lambda Configuration", lambda_result))
    
    print()
    print("=" * 50)
    print("DEPLOYMENT TEST SUMMARY:")
    
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"- {name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("All MCP servers are ready for deployment!")
    else:
        print("Some tests failed. Please check the errors above.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)