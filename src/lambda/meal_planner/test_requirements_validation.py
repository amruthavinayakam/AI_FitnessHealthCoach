#!/usr/bin/env python3
"""
Test script to validate specific requirements for task 5.2:
- Connect meal planner to Spoonacular MCP server for caching
- Implement nutritional optimization based on fitness goals  
- Add dietary restriction handling and meal balancing
- Requirements: 3.1, 3.2, 3.3, 3.4
"""
import asyncio
import json
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp_servers', 'spoonacular_enhanced'))

from handler import MealPlannerService

async def test_requirement_3_1():
    """
    Requirement 3.1: THE Fitness Health Coach System SHALL use the Spoonacular API 
    to generate a 7-day meal plan with breakfast, lunch, and dinner for each day
    """
    print("Testing Requirement 3.1: 7-day meal plan generation...")
    
    meal_planner = MealPlannerService()
    user_profile = {
        'username': 'req_test_user',
        'user_id': 'req_test_123',
        'query': 'Generate a weekly meal plan',
        'timestamp': 'test_timestamp'
    }
    
    try:
        result = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['omnivore'],
            calorie_target=2000,
            fitness_goals='maintenance',
            days=7
        )
        
        meal_plan = result['meal_plan']
        weekly_plan = meal_plan.get('weekly_plan', [])
        
        # Validate 7-day plan
        assert len(weekly_plan) == 7, f"Expected 7 days, got {len(weekly_plan)}"
        
        # Validate each day has breakfast, lunch, and dinner
        for i, day_plan in enumerate(weekly_plan):
            assert 'breakfast' in day_plan, f"Day {i+1} missing breakfast"
            assert 'lunch' in day_plan, f"Day {i+1} missing lunch"
            assert 'dinner' in day_plan, f"Day {i+1} missing dinner"
            
            # Validate meal structure
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                meal = day_plan[meal_type]
                assert 'title' in meal, f"Day {i+1} {meal_type} missing title"
                assert 'calories_per_serving' in meal, f"Day {i+1} {meal_type} missing calories"
        
        print("✓ Requirement 3.1 PASSED: 7-day meal plan with 3 meals per day generated")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 3.1 FAILED: {e}")
        return False

async def test_requirement_3_2():
    """
    Requirement 3.2: THE Fitness Health Coach System SHALL retrieve nutritional 
    information and portion guidelines from the Spoonacular API for each meal
    """
    print("Testing Requirement 3.2: Nutritional information retrieval...")
    
    meal_planner = MealPlannerService()
    user_profile = {
        'username': 'req_test_user',
        'user_id': 'req_test_123',
        'query': 'I need detailed nutrition info',
        'timestamp': 'test_timestamp'
    }
    
    try:
        result = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['omnivore'],
            calorie_target=2000,
            fitness_goals='maintenance',
            days=3
        )
        
        meal_plan = result['meal_plan']
        weekly_plan = meal_plan.get('weekly_plan', [])
        
        # Validate nutritional information is present
        for i, day_plan in enumerate(weekly_plan):
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                meal = day_plan[meal_type]
                
                # Check for required nutritional fields
                required_fields = ['calories_per_serving', 'protein_g', 'carbs_g', 'fat_g']
                for field in required_fields:
                    assert field in meal, f"Day {i+1} {meal_type} missing {field}"
                    assert isinstance(meal[field], (int, float)), f"Day {i+1} {meal_type} {field} not numeric"
                    assert meal[field] >= 0, f"Day {i+1} {meal_type} {field} negative value"
            
            # Check daily totals
            assert 'total_calories' in day_plan, f"Day {i+1} missing total_calories"
            assert 'total_protein' in day_plan, f"Day {i+1} missing total_protein"
            assert 'total_carbs' in day_plan, f"Day {i+1} missing total_carbs"
            assert 'total_fat' in day_plan, f"Day {i+1} missing total_fat"
        
        # Validate nutrition analysis is provided
        assert 'nutrition_analysis' in result, "Missing nutrition analysis"
        analysis = result['nutrition_analysis']
        assert 'analysis_summary' in analysis, "Missing analysis summary"
        
        summary = analysis['analysis_summary']
        required_summary_fields = ['avg_daily_calories', 'avg_daily_protein', 'avg_daily_carbs', 'avg_daily_fat']
        for field in required_summary_fields:
            assert field in summary, f"Missing {field} in analysis summary"
        
        print("✓ Requirement 3.2 PASSED: Nutritional information and analysis provided")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 3.2 FAILED: {e}")
        return False

async def test_requirement_3_3():
    """
    Requirement 3.3: THE Fitness Health Coach System SHALL configure Spoonacular API 
    requests to align meal recommendations with the user's fitness goals and dietary preferences
    """
    print("Testing Requirement 3.3: Fitness goal and dietary preference alignment...")
    
    meal_planner = MealPlannerService()
    
    # Test different fitness goals
    fitness_goals = ['weight_loss', 'muscle_gain', 'maintenance', 'endurance']
    dietary_preferences_list = [['vegetarian'], ['vegan'], ['ketogenic'], ['omnivore']]
    
    try:
        for fitness_goal in fitness_goals:
            for dietary_preferences in dietary_preferences_list:
                user_profile = {
                    'username': f'test_{fitness_goal}_{dietary_preferences[0]}',
                    'user_id': f'test_{fitness_goal}_{dietary_preferences[0]}_123',
                    'query': f'I want {fitness_goal} with {dietary_preferences[0]} diet',
                    'timestamp': 'test_timestamp'
                }
                
                result = await meal_planner.generate_meal_plan(
                    user_profile=user_profile,
                    dietary_preferences=dietary_preferences,
                    calorie_target=2000,
                    fitness_goals=fitness_goal,
                    days=2  # Shorter for testing
                )
                
                meal_plan = result['meal_plan']
                
                # Validate fitness goal is recorded
                assert meal_plan.get('fitness_goal') == fitness_goal, f"Fitness goal not recorded correctly"
                
                # Validate dietary preferences are recorded
                assert meal_plan.get('dietary_preferences') == dietary_preferences, f"Dietary preferences not recorded"
                
                # Validate MCP server optimization was applied
                assert result.get('optimization_applied', False), f"Optimization not applied for {fitness_goal} + {dietary_preferences}"
        
        print("✓ Requirement 3.3 PASSED: Meal recommendations aligned with fitness goals and dietary preferences")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 3.3 FAILED: {e}")
        return False

async def test_requirement_3_4():
    """
    Requirement 3.4: THE Fitness Health Coach System SHALL ensure Spoonacular API-generated 
    meal plans provide balanced nutrition across macronutrients
    """
    print("Testing Requirement 3.4: Balanced nutrition across macronutrients...")
    
    meal_planner = MealPlannerService()
    
    # Clear cache to ensure fresh calculation
    if meal_planner.mcp_server:
        await meal_planner.mcp_server.clear_cache()
    
    user_profile = {
        'username': 'balance_test_user_fresh',
        'user_id': 'balance_test_123_fresh',
        'query': 'I need a balanced meal plan',
        'timestamp': 'test_timestamp_fresh'
    }
    
    try:
        result = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['omnivore'],
            calorie_target=2000,
            fitness_goals='maintenance',
            days=7
        )
        
        # Validate nutrition analysis provides balance information
        assert 'nutrition_analysis' in result, "Missing nutrition analysis"
        analysis = result['nutrition_analysis']
        
        # Check for macronutrient ratios
        if 'macronutrient_ratios' in analysis:
            ratios = analysis['macronutrient_ratios']
            
            # Validate ratios are present and reasonable
            assert 'protein_percent' in ratios, "Missing protein percentage"
            assert 'carb_percent' in ratios, "Missing carb percentage"
            assert 'fat_percent' in ratios, "Missing fat percentage"
            
            # Check that ratios are within reasonable ranges
            protein_pct = ratios['protein_percent']
            carb_pct = ratios['carb_percent']
            fat_pct = ratios['fat_percent']
            
            assert 10 <= protein_pct <= 40, f"Protein percentage out of range: {protein_pct}%"
            assert 20 <= carb_pct <= 70, f"Carb percentage out of range: {carb_pct}%"
            assert 15 <= fat_pct <= 45, f"Fat percentage out of range: {fat_pct}%"
            
            # Check that percentages roughly add up to 100% (allowing for rounding)
            total_pct = protein_pct + carb_pct + fat_pct
            assert 90 <= total_pct <= 110, f"Macronutrient percentages don't add up properly: {total_pct}%"
        
        # Check for balance score
        balance_score = analysis.get('balance_score', 0)
        assert balance_score > 0, "Balance score should be positive"
        
        # Check for recommendations if balance is poor
        if balance_score < 70:
            assert 'recommendations' in analysis, "Should provide recommendations for poor balance"
            assert len(analysis['recommendations']) > 0, "Should have specific recommendations"
        
        print(f"✓ Requirement 3.4 PASSED: Balanced nutrition provided (balance score: {balance_score:.1f}%)")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 3.4 FAILED: {e}")
        return False

async def test_mcp_caching_functionality():
    """
    Test the MCP server caching functionality specifically
    """
    print("Testing MCP Server Caching Functionality...")
    
    meal_planner = MealPlannerService()
    user_profile = {
        'username': 'cache_test_user',
        'user_id': 'cache_test_123',
        'query': 'Test caching',
        'timestamp': 'test_timestamp'
    }
    
    try:
        # First request - should not be cached
        result1 = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['vegetarian'],
            calorie_target=2000,
            fitness_goals='muscle_gain',
            days=3
        )
        
        assert not result1.get('cached', True), "First request should not be cached"
        
        # Second identical request - should be cached
        result2 = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['vegetarian'],
            calorie_target=2000,
            fitness_goals='muscle_gain',
            days=3
        )
        
        assert result2.get('cached', False), "Second identical request should be cached"
        
        # Different request - should not be cached
        result3 = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['vegan'],  # Different preference
            calorie_target=2000,
            fitness_goals='muscle_gain',
            days=3
        )
        
        assert not result3.get('cached', True), "Different request should not be cached"
        
        print("✓ MCP Server Caching: Working correctly")
        return True
        
    except Exception as e:
        print(f"✗ MCP Server Caching FAILED: {e}")
        return False

async def test_dietary_restriction_handling():
    """
    Test dietary restriction handling functionality
    """
    print("Testing Dietary Restriction Handling...")
    
    meal_planner = MealPlannerService()
    
    # Test various dietary restrictions
    dietary_tests = [
        (['vegetarian'], 'vegetarian meals'),
        (['vegan'], 'vegan meals'),
        (['ketogenic'], 'keto meals'),
        (['paleo'], 'paleo meals'),
        (['mediterranean'], 'mediterranean meals')
    ]
    
    try:
        for dietary_prefs, description in dietary_tests:
            user_profile = {
                'username': f'diet_test_{dietary_prefs[0]}',
                'user_id': f'diet_test_{dietary_prefs[0]}_123',
                'query': f'I need {description}',
                'timestamp': 'test_timestamp'
            }
            
            result = await meal_planner.generate_meal_plan(
                user_profile=user_profile,
                dietary_preferences=dietary_prefs,
                calorie_target=2000,
                fitness_goals='maintenance',
                days=2
            )
            
            # Validate dietary preferences are respected
            meal_plan = result['meal_plan']
            assert meal_plan.get('dietary_preferences') == dietary_prefs, f"Dietary preferences not preserved for {dietary_prefs}"
            
            # Test recipe suggestions with dietary restrictions
            recipe_result = await meal_planner.get_recipe_suggestions(
                calorie_range=(300, 600),
                dietary_preferences=dietary_prefs,
                meal_type='lunch'
            )
            
            # Should return recipes (even if limited for some diets)
            assert 'recipes' in recipe_result, f"No recipes returned for {dietary_prefs}"
        
        print("✓ Dietary Restriction Handling: Working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Dietary Restriction Handling FAILED: {e}")
        return False

async def main():
    """Main test function for requirements validation"""
    print("=" * 70)
    print("Task 5.2 Requirements Validation Test Suite")
    print("Spoonacular MCP Server Integration Requirements")
    print("=" * 70)
    
    # Test each requirement
    tests = [
        ("Requirement 3.1", test_requirement_3_1),
        ("Requirement 3.2", test_requirement_3_2),
        ("Requirement 3.3", test_requirement_3_3),
        ("Requirement 3.4", test_requirement_3_4),
        ("MCP Caching", test_mcp_caching_functionality),
        ("Dietary Restrictions", test_dietary_restriction_handling)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 50}")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("REQUIREMENTS VALIDATION SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        icon = "✓" if passed else "✗"
        print(f"{icon} {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL REQUIREMENTS VALIDATED SUCCESSFULLY!")
        print("\nTask 5.2 Implementation Summary:")
        print("✓ Connected meal planner to Spoonacular MCP server for caching")
        print("✓ Implemented nutritional optimization based on fitness goals")
        print("✓ Added dietary restriction handling and meal balancing")
        print("✓ All requirements 3.1, 3.2, 3.3, 3.4 are satisfied")
    else:
        print("❌ Some requirements validation failed. Please review implementation.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)