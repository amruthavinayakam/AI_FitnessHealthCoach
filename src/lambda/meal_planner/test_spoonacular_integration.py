#!/usr/bin/env python3
"""
Unit tests for Spoonacular integration in meal planner
Task 5.3: Write unit tests for Spoonacular integration
- Mock Spoonacular API calls for testing
- Test meal plan generation and nutritional analysis
- Validate meal plan structure and nutritional balance
- Requirements: 3.1, 3.2
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp_servers', 'spoonacular_enhanced'))

from handler import MealPlannerService, lambda_handler
from server import SpoonacularEnhancedMCPServer

class TestSpoonacularIntegration(unittest.TestCase):
    """Unit tests for Spoonacular API integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.meal_planner = MealPlannerService()
        self.test_user_profile = {
            'username': 'test_user',
            'user_id': 'test_123',
            'query': 'I want a balanced meal plan',
            'timestamp': 'test_timestamp'
        }
    
    def test_meal_planner_initialization(self):
        """Test MealPlannerService initialization"""
        self.assertIsInstance(self.meal_planner, MealPlannerService)
        self.assertIsNotNone(self.meal_planner.mcp_server)
        self.assertIsInstance(self.meal_planner.mcp_server, SpoonacularEnhancedMCPServer)
    
    def test_generate_meal_plan_structure(self):
        """Test meal plan generation returns correct structure (Requirement 3.1)"""
        async def run_test():
            result = await self.meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=7
            )
            
            # Validate top-level structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('meal_plan', result)
            self.assertIn('nutrition_analysis', result)
            self.assertTrue(result['success'])
            
            # Validate meal plan structure (Requirement 3.1)
            meal_plan = result['meal_plan']
            self.assertIn('weekly_plan', meal_plan)
            self.assertIn('user_id', meal_plan)
            self.assertIn('username', meal_plan)
            
            # Validate 7-day plan with 3 meals per day
            weekly_plan = meal_plan['weekly_plan']
            self.assertEqual(len(weekly_plan), 7, "Should have 7 days")
            
            for i, day_plan in enumerate(weekly_plan):
                with self.subTest(day=i+1):
                    self.assertIn('breakfast', day_plan, f"Day {i+1} missing breakfast")
                    self.assertIn('lunch', day_plan, f"Day {i+1} missing lunch")
                    self.assertIn('dinner', day_plan, f"Day {i+1} missing dinner")
                    self.assertIn('total_calories', day_plan, f"Day {i+1} missing total_calories")
        
        asyncio.run(run_test())
    
    def test_nutritional_information_structure(self):
        """Test nutritional information is properly retrieved (Requirement 3.2)"""
        async def run_test():
            result = await self.meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=3
            )
            
            meal_plan = result['meal_plan']
            weekly_plan = meal_plan['weekly_plan']
            
            # Validate nutritional information for each meal (Requirement 3.2)
            for i, day_plan in enumerate(weekly_plan):
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    meal = day_plan[meal_type]
                    with self.subTest(day=i+1, meal=meal_type):
                        # Required nutritional fields
                        self.assertIn('calories_per_serving', meal)
                        self.assertIn('protein_g', meal)
                        self.assertIn('carbs_g', meal)
                        self.assertIn('fat_g', meal)
                        
                        # Validate data types and ranges
                        self.assertIsInstance(meal['calories_per_serving'], (int, float))
                        self.assertIsInstance(meal['protein_g'], (int, float))
                        self.assertIsInstance(meal['carbs_g'], (int, float))
                        self.assertIsInstance(meal['fat_g'], (int, float))
                        
                        # Nutritional values should be positive
                        self.assertGreaterEqual(meal['calories_per_serving'], 0)
                        self.assertGreaterEqual(meal['protein_g'], 0)
                        self.assertGreaterEqual(meal['carbs_g'], 0)
                        self.assertGreaterEqual(meal['fat_g'], 0)
                
                # Validate daily totals
                self.assertIn('total_calories', day_plan)
                self.assertIn('total_protein', day_plan)
                self.assertIn('total_carbs', day_plan)
                self.assertIn('total_fat', day_plan)
        
        asyncio.run(run_test())
    
    def test_nutrition_analysis_structure(self):
        """Test nutrition analysis provides comprehensive information"""
        async def run_test():
            result = await self.meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=7
            )
            
            # Validate nutrition analysis structure
            self.assertIn('nutrition_analysis', result)
            analysis = result['nutrition_analysis']
            
            # Required analysis components
            self.assertIn('analysis_summary', analysis)
            self.assertIn('balance_score', analysis)
            
            # Analysis summary should contain averages
            summary = analysis['analysis_summary']
            required_fields = ['avg_daily_calories', 'avg_daily_protein', 'avg_daily_carbs', 'avg_daily_fat']
            for field in required_fields:
                self.assertIn(field, summary)
                self.assertIsInstance(summary[field], (int, float))
                self.assertGreaterEqual(summary[field], 0)
            
            # Balance score should be a percentage
            balance_score = analysis['balance_score']
            self.assertIsInstance(balance_score, (int, float))
            self.assertGreaterEqual(balance_score, 0)
            self.assertLessEqual(balance_score, 100)
        
        asyncio.run(run_test())
    
    def test_macronutrient_balance_validation(self):
        """Test macronutrient balance calculation and validation"""
        async def run_test():
            result = await self.meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=7
            )
            
            analysis = result['nutrition_analysis']
            
            # Check for macronutrient ratios if available
            if 'macronutrient_ratios' in analysis:
                ratios = analysis['macronutrient_ratios']
                
                self.assertIn('protein_percent', ratios)
                self.assertIn('carb_percent', ratios)
                self.assertIn('fat_percent', ratios)
                
                protein_pct = ratios['protein_percent']
                carb_pct = ratios['carb_percent']
                fat_pct = ratios['fat_percent']
                
                # Validate percentage ranges
                self.assertIsInstance(protein_pct, (int, float))
                self.assertIsInstance(carb_pct, (int, float))
                self.assertIsInstance(fat_pct, (int, float))
                
                # Percentages should be reasonable
                self.assertGreaterEqual(protein_pct, 0)
                self.assertGreaterEqual(carb_pct, 0)
                self.assertGreaterEqual(fat_pct, 0)
                self.assertLessEqual(protein_pct, 100)
                self.assertLessEqual(carb_pct, 100)
                self.assertLessEqual(fat_pct, 100)
                
                # Total should be approximately 100% (allowing for rounding)
                total_pct = protein_pct + carb_pct + fat_pct
                self.assertGreaterEqual(total_pct, 90)
                self.assertLessEqual(total_pct, 110)
        
        asyncio.run(run_test())
    
    def test_dietary_preferences_handling(self):
        """Test dietary preference parsing and handling"""
        test_cases = [
            ("I'm vegetarian", ['vegetarian']),
            ("vegan meal plan", ['vegan']),
            ("keto diet", ['ketogenic']),
            ("paleo lifestyle", ['paleo']),
            ("mediterranean diet", ['mediterranean']),
            ("regular diet", ['omnivore'])
        ]
        
        for query, expected_prefs in test_cases:
            with self.subTest(query=query):
                parsed_prefs = self.meal_planner._parse_dietary_preferences(query)
                self.assertEqual(parsed_prefs, expected_prefs)
    
    def test_fitness_goal_extraction(self):
        """Test fitness goal extraction from user queries"""
        test_cases = [
            ("I want to lose weight", 'weight_loss'),
            ("help me build muscle", 'muscle_gain'),
            ("maintain my current weight", 'maintenance'),
            ("training for marathon", 'endurance'),
            ("general fitness", 'maintenance')  # default
        ]
        
        for query, expected_goal in test_cases:
            with self.subTest(query=query):
                extracted_goal = self.meal_planner._extract_fitness_goal(query)
                self.assertEqual(extracted_goal, expected_goal)
    
    def test_calorie_target_extraction(self):
        """Test calorie target extraction and defaults"""
        # Test explicit calorie mention
        query_with_calories = "I need 2200 calories per day"
        extracted_calories = self.meal_planner._extract_calorie_target(query_with_calories, 'maintenance')
        self.assertEqual(extracted_calories, 2200)
        
        # Test default based on fitness goal
        query_without_calories = "I want to gain muscle"
        extracted_calories = self.meal_planner._extract_calorie_target(query_without_calories, 'muscle_gain')
        self.assertEqual(extracted_calories, 2400)  # Default for muscle gain
    
    @patch('server.SpoonacularEnhancedMCPServer')
    def test_mcp_server_integration_mock(self, mock_mcp_class):
        """Test MCP server integration with mocked responses"""
        # Setup mock MCP server
        mock_mcp_instance = AsyncMock()
        mock_mcp_class.return_value = mock_mcp_instance
        
        # Mock meal plan response
        mock_meal_plan = {
            'weekly_plan': [
                {
                    'day': 'Day 1',
                    'breakfast': {'title': 'Mock Breakfast', 'calories_per_serving': 300, 'protein_g': 15, 'carbs_g': 40, 'fat_g': 8},
                    'lunch': {'title': 'Mock Lunch', 'calories_per_serving': 500, 'protein_g': 25, 'carbs_g': 60, 'fat_g': 15},
                    'dinner': {'title': 'Mock Dinner', 'calories_per_serving': 600, 'protein_g': 30, 'carbs_g': 70, 'fat_g': 20},
                    'total_calories': 1400,
                    'total_protein': 70,
                    'total_carbs': 170,
                    'total_fat': 43
                }
            ],
            'nutrition_score': 85.0,
            'fitness_goal': 'maintenance',
            'dietary_preferences': ['omnivore'],
            'days': 1
        }
        
        mock_mcp_instance.get_optimized_meal_plan.return_value = {
            'cached': False,
            'meal_plan': mock_meal_plan
        }
        
        mock_mcp_instance.analyze_nutrition_balance.return_value = {
            'analysis_summary': {
                'avg_daily_calories': 1400,
                'avg_daily_protein': 70,
                'avg_daily_carbs': 170,
                'avg_daily_fat': 43
            },
            'balance_score': 85.0,
            'recommendations': []
        }
        
        async def run_test():
            # Create new meal planner with mocked MCP server
            meal_planner = MealPlannerService()
            meal_planner.mcp_server = mock_mcp_instance
            
            result = await meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=1
            )
            
            # Verify MCP server methods were called
            mock_mcp_instance.get_optimized_meal_plan.assert_called_once()
            mock_mcp_instance.analyze_nutrition_balance.assert_called_once()
            
            # Verify result structure
            self.assertTrue(result['success'])
            self.assertIn('meal_plan', result)
            self.assertIn('nutrition_analysis', result)
            self.assertEqual(result['optimization_applied'], True)
        
        asyncio.run(run_test())
    
    def test_meal_optimization_functionality(self):
        """Test meal optimization for specific fitness goals"""
        async def run_test():
            sample_meal = {
                "title": "Test Meal",
                "calories_per_serving": 400,
                "protein_g": 15.0,
                "carbs_g": 50.0,
                "fat_g": 12.0
            }
            
            result = await self.meal_planner.optimize_meal_for_goals(
                current_meal=sample_meal,
                fitness_goal='muscle_gain',
                target_calories=500
            )
            
            # Validate optimization result structure
            self.assertIsInstance(result, dict)
            self.assertIn('current_nutrition', result)
            self.assertIn('optimization_suggestions', result)
            self.assertIn('optimization_score', result)
            
            # Optimization score should be a percentage
            score = result['optimization_score']
            self.assertIsInstance(score, (int, float))
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)
        
        asyncio.run(run_test())
    
    def test_recipe_suggestions_functionality(self):
        """Test recipe suggestions with dietary restrictions"""
        async def run_test():
            result = await self.meal_planner.get_recipe_suggestions(
                calorie_range=(300, 600),
                dietary_preferences=['vegetarian'],
                meal_type='lunch'
            )
            
            # Validate result structure
            self.assertIsInstance(result, dict)
            self.assertIn('recipes', result)
            self.assertIn('count', result)
            
            # Validate recipes are within calorie range
            recipes = result['recipes']
            for recipe in recipes:
                calories = recipe['calories_per_serving']
                self.assertGreaterEqual(calories, 300)
                self.assertLessEqual(calories, 600)
        
        asyncio.run(run_test())
    
    def test_lambda_handler_integration(self):
        """Test Lambda handler with Spoonacular integration"""
        test_event = {
            'body': json.dumps({
                'username': 'test_user',
                'userId': 'test_123',
                'query': 'I want vegetarian meals for muscle gain'
            })
        }
        
        class MockContext:
            aws_request_id = 'test-request-123'
        
        result = lambda_handler(test_event, MockContext())
        
        # Validate Lambda response structure
        self.assertIsInstance(result, dict)
        self.assertIn('statusCode', result)
        self.assertIn('body', result)
        
        # Should return success
        self.assertEqual(result['statusCode'], 200)
        
        # Parse response body
        body = json.loads(result['body'])
        self.assertIn('success', body)
        self.assertTrue(body['success'])
        self.assertIn('data', body)
        self.assertIn('message', body)
        
        # Validate data structure
        data = body['data']
        self.assertIn('meal_plan', data)
        self.assertIn('nutrition_analysis', data)
        self.assertIn('metadata', data)
        
        # Validate metadata
        metadata = data['metadata']
        self.assertIn('dietary_preferences', metadata)
        self.assertIn('fitness_goal', metadata)
        self.assertIn('calorie_target', metadata)
        self.assertIn('optimization_applied', metadata)
        self.assertIn('cached', metadata)
    
    def test_error_handling_invalid_input(self):
        """Test error handling for invalid inputs"""
        # Test missing query
        test_event = {
            'body': json.dumps({
                'username': 'test_user',
                'userId': 'test_123'
                # Missing query
            })
        }
        
        class MockContext:
            aws_request_id = 'test-request-123'
        
        result = lambda_handler(test_event, MockContext())
        
        # Should return error
        self.assertEqual(result['statusCode'], 400)
        body = json.loads(result['body'])
        self.assertFalse(body['success'])
        self.assertIn('error', body)
    
    def test_fallback_without_mcp_server(self):
        """Test fallback functionality when MCP server is unavailable"""
        async def run_test():
            # Create meal planner without MCP server
            meal_planner = MealPlannerService()
            meal_planner.mcp_server = None
            
            result = await meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=3
            )
            
            # Should still work with fallback
            self.assertTrue(result['success'])
            self.assertIn('meal_plan', result)
            self.assertIn('nutrition_analysis', result)
            self.assertFalse(result['optimization_applied'])
            self.assertFalse(result['cached'])
        
        asyncio.run(run_test())
    
    def test_caching_behavior(self):
        """Test MCP server caching behavior"""
        async def run_test():
            # Clear cache first
            if self.meal_planner.mcp_server:
                await self.meal_planner.mcp_server.clear_cache()
            
            # First request should not be cached
            result1 = await self.meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['vegetarian'],
                calorie_target=1800,
                fitness_goals='weight_loss',
                days=2
            )
            
            # Second identical request should be cached
            result2 = await self.meal_planner.generate_meal_plan(
                user_profile=self.test_user_profile,
                dietary_preferences=['vegetarian'],
                calorie_target=1800,
                fitness_goals='weight_loss',
                days=2
            )
            
            # Verify caching behavior
            if self.meal_planner.mcp_server:
                # With MCP server, second request should be cached
                self.assertTrue(result2.get('cached', False))
            else:
                # Without MCP server, caching is not available
                self.assertFalse(result2.get('cached', False))
        
        asyncio.run(run_test())

class TestSpoonacularMCPServerUnit(unittest.TestCase):
    """Unit tests specifically for SpoonacularEnhancedMCPServer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = SpoonacularEnhancedMCPServer()
    
    def test_nutrition_target_calculation(self):
        """Test nutrition target calculations for different fitness goals"""
        from server import FitnessGoal
        
        # Test muscle gain targets
        targets = self.server._calculate_nutrition_targets(2000, FitnessGoal.MUSCLE_GAIN)
        self.assertEqual(targets.calories, 2000)
        self.assertGreater(targets.protein_g, 100)  # Higher protein for muscle gain
        
        # Test weight loss targets
        targets = self.server._calculate_nutrition_targets(1800, FitnessGoal.WEIGHT_LOSS)
        self.assertEqual(targets.calories, 1800)
        self.assertGreater(targets.protein_g, 0)
    
    def test_recipe_filtering(self):
        """Test recipe filtering by dietary preferences"""
        # Test vegetarian filtering
        vegetarian_recipes = self.server._filter_recipes_by_diet(['vegetarian'])
        for recipe in vegetarian_recipes:
            self.assertIn('vegetarian', recipe.diet_types)
        
        # Test omnivore (should include all recipes)
        omnivore_recipes = self.server._filter_recipes_by_diet(['omnivore'])
        self.assertGreater(len(omnivore_recipes), 0)
    
    def test_nutrition_score_calculation(self):
        """Test nutrition score calculation"""
        from server import NutritionTarget
        
        targets = NutritionTarget(
            calories=2000,
            protein_g=150,
            carbs_g=250,
            fat_g=67,
            fiber_g=28
        )
        
        # Perfect match should score 100%
        perfect_nutrition = {
            "calories": 2000,
            "protein": 150,
            "carbs": 250,
            "fat": 67
        }
        
        score = self.server._calculate_nutrition_score(perfect_nutrition, targets, 1)
        self.assertGreaterEqual(score, 95)  # Should be very high for perfect match
    
    def test_meal_plan_generation_async(self):
        """Test async meal plan generation"""
        async def run_test():
            result = await self.server.get_optimized_meal_plan(
                dietary_preferences=['omnivore'],
                calorie_target=2000,
                fitness_goals='maintenance',
                days=3
            )
            
            self.assertIn('meal_plan', result)
            self.assertIn('cached', result)
            
            meal_plan = result['meal_plan']
            self.assertIn('weekly_plan', meal_plan)
            self.assertEqual(len(meal_plan['weekly_plan']), 3)
        
        asyncio.run(run_test())

def run_tests():
    """Run all unit tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSpoonacularIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSpoonacularMCPServerUnit))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)