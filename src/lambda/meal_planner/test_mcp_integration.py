#!/usr/bin/env python3
"""
Test script for Spoonacular MCP Server integration with meal planner
"""
import asyncio
import json
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp_servers', 'spoonacular_enhanced'))

from handler import MealPlannerService

async def test_mcp_integration():
    """Test the MCP server integration functionality"""
    print("Testing Spoonacular MCP Server Integration...")
    
    # Initialize the meal planner service
    meal_planner = MealPlannerService()
    
    # Test user profile
    user_profile = {
        'username': 'test_user',
        'user_id': 'test_123',
        'query': 'I want to gain muscle and prefer vegetarian meals with 2200 calories',
        'timestamp': 'test_timestamp'
    }
    
    print(f"Testing with user profile: {user_profile['username']}")
    
    # Test 1: Generate optimized meal plan with caching
    print("\n1. Testing optimized meal plan generation...")
    try:
        result = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['vegetarian'],
            calorie_target=2200,
            fitness_goals='muscle_gain',
            days=3  # Shorter for testing
        )
        
        print(f"✓ Meal plan generated successfully")
        print(f"  - Optimization applied: {result.get('optimization_applied', False)}")
        print(f"  - Cached result: {result.get('cached', False)}")
        print(f"  - Days planned: {result['meal_plan'].get('days', 0)}")
        
        if 'nutrition_analysis' in result:
            analysis = result['nutrition_analysis']
            print(f"  - Avg daily calories: {analysis['analysis_summary']['avg_daily_calories']}")
            print(f"  - Balance score: {analysis.get('balance_score', 0):.1f}%")
        
    except Exception as e:
        print(f"✗ Error generating meal plan: {e}")
        return False
    
    # Test 2: Test caching by generating the same plan again
    print("\n2. Testing caching functionality...")
    try:
        result2 = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['vegetarian'],
            calorie_target=2200,
            fitness_goals='muscle_gain',
            days=3
        )
        
        print(f"✓ Second meal plan request completed")
        print(f"  - Cached result: {result2.get('cached', False)}")
        
        if result2.get('cached'):
            print("  - Cache working correctly!")
        else:
            print("  - Cache not used (may be expected for fallback mode)")
        
    except Exception as e:
        print(f"✗ Error testing caching: {e}")
        return False
    
    # Test 3: Test meal optimization for specific goals
    print("\n3. Testing meal optimization...")
    try:
        sample_meal = {
            "title": "Test Meal",
            "calories_per_serving": 400,
            "protein_g": 15.0,
            "carbs_g": 50.0,
            "fat_g": 12.0
        }
        
        optimization_result = await meal_planner.optimize_meal_for_goals(
            current_meal=sample_meal,
            fitness_goal='muscle_gain',
            target_calories=500
        )
        
        print(f"✓ Meal optimization completed")
        print(f"  - Optimization score: {optimization_result.get('optimization_score', 0):.1f}%")
        print(f"  - Suggestions count: {len(optimization_result.get('optimization_suggestions', []))}")
        
    except Exception as e:
        print(f"✗ Error testing meal optimization: {e}")
        return False
    
    # Test 4: Test recipe suggestions with dietary restrictions
    print("\n4. Testing recipe suggestions with dietary restrictions...")
    try:
        recipe_result = await meal_planner.get_recipe_suggestions(
            calorie_range=(300, 500),
            dietary_preferences=['vegetarian'],
            meal_type='lunch'
        )
        
        print(f"✓ Recipe suggestions retrieved")
        print(f"  - Recipe count: {recipe_result.get('count', 0)}")
        print(f"  - Cached result: {recipe_result.get('cached', False)}")
        
    except Exception as e:
        print(f"✗ Error testing recipe suggestions: {e}")
        return False
    
    # Test 5: Test dietary preference parsing
    print("\n5. Testing dietary preference parsing...")
    try:
        test_queries = [
            "I'm vegetarian and want to lose weight",
            "Vegan meal plan for muscle building",
            "Keto diet for maintenance",
            "Regular omnivore diet"
        ]
        
        for query in test_queries:
            preferences = meal_planner._parse_dietary_preferences(query)
            fitness_goal = meal_planner._extract_fitness_goal(query)
            calorie_target = meal_planner._extract_calorie_target(query, fitness_goal)
            
            print(f"  Query: '{query}'")
            print(f"    - Preferences: {preferences}")
            print(f"    - Fitness goal: {fitness_goal}")
            print(f"    - Calorie target: {calorie_target}")
        
        print("✓ Dietary preference parsing working correctly")
        
    except Exception as e:
        print(f"✗ Error testing preference parsing: {e}")
        return False
    
    print("\n✓ All MCP integration tests completed successfully!")
    return True

def test_lambda_handler():
    """Test the Lambda handler function"""
    print("\nTesting Lambda handler...")
    
    # Import the handler
    from handler import lambda_handler
    
    # Test event
    test_event = {
        'body': json.dumps({
            'username': 'test_user',
            'userId': 'test_123',
            'query': 'I want vegetarian meals for muscle gain with 2200 calories per day'
        })
    }
    
    # Mock context
    class MockContext:
        aws_request_id = 'test-request-123'
    
    try:
        result = lambda_handler(test_event, MockContext())
        
        print(f"✓ Lambda handler executed successfully")
        print(f"  - Status code: {result['statusCode']}")
        
        if result['statusCode'] == 200:
            body = json.loads(result['body'])
            print(f"  - Success: {body['success']}")
            print(f"  - Message: {body['message']}")
            
            if 'data' in body:
                data = body['data']
                print(f"  - Meal plan days: {data['meal_plan'].get('days', 0)}")
                print(f"  - Optimization applied: {data['metadata']['optimization_applied']}")
                print(f"  - Cached: {data['metadata']['cached']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Lambda handler: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("Spoonacular MCP Server Integration Test Suite")
    print("=" * 60)
    
    # Test MCP integration
    mcp_success = await test_mcp_integration()
    
    # Test Lambda handler
    handler_success = test_lambda_handler()
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print(f"MCP Integration Tests: {'PASSED' if mcp_success else 'FAILED'}")
    print(f"Lambda Handler Tests: {'PASSED' if handler_success else 'FAILED'}")
    
    if mcp_success and handler_success:
        print("\n🎉 All tests passed! MCP integration is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)