"""
Unit tests for Spoonacular Enhanced MCP Server
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add the server module to path
sys.path.insert(0, os.path.dirname(__file__))
from server import SpoonacularEnhancedMCPServer, FitnessGoal, DietType, CacheEntry

class TestSpoonacularEnhancedMCPServer(unittest.TestCase):
    """Test cases for Spoonacular Enhanced MCP Server"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = SpoonacularEnhancedMCPServer()
    
    def test_server_initialization(self):
        """Test that server initializes properly"""
        self.assertIsInstance(self.server.cache, dict)
        self.assertIsInstance(self.server.sample_recipes, dict)
        self.assertGreater(len(self.server.sample_recipes), 0)
        self.assertIsInstance(self.server.fitness_goal_multipliers, dict)
    
    def test_sample_recipes_initialization(self):
        """Test sample recipe database initialization"""
        self.assertIn("oatmeal_berries", self.server.sample_recipes)
        self.assertIn("chicken_quinoa_bowl", self.server.sample_recipes)
        
        # Check recipe structure
        recipe = self.server.sample_recipes["oatmeal_berries"]
        self.assertEqual(recipe.title, "Overnight Oats with Berries")
        self.assertIsInstance(recipe.calories_per_serving, int)
        self.assertIsInstance(recipe.protein_g, float)
        self.assertIsInstance(recipe.ingredients, list)
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        key1 = self.server._generate_cache_key("test", 123, ["a", "b"])
        key2 = self.server._generate_cache_key("test", 123, ["a", "b"])
        key3 = self.server._generate_cache_key("different", 123, ["a", "b"])
        
        # Same inputs should generate same key
        self.assertEqual(key1, key2)
        # Different inputs should generate different keys
        self.assertNotEqual(key1, key3)
    
    def test_cache_operations(self):
        """Test cache set and get operations"""
        test_data = {"test": "data"}
        cache_key = "test_key"
        
        # Test cache miss
        result = self.server._get_from_cache(cache_key)
        self.assertIsNone(result)
        
        # Test cache set and hit
        self.server._set_cache(cache_key, test_data, ttl_seconds=3600)
        result = self.server._get_from_cache(cache_key)
        self.assertEqual(result, test_data)
    
    def test_cache_expiration(self):
        """Test cache entry expiration"""
        test_data = {"test": "data"}
        cache_key = "test_key_expire"
        
        # Set cache with very short TTL
        self.server._set_cache(cache_key, test_data, ttl_seconds=0.1)
        
        # Should be available immediately
        result = self.server._get_from_cache(cache_key)
        self.assertEqual(result, test_data)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        result = self.server._get_from_cache(cache_key)
        self.assertIsNone(result)
    
    def test_calculate_nutrition_targets(self):
        """Test nutrition target calculations"""
        targets = self.server._calculate_nutrition_targets(2000, FitnessGoal.MUSCLE_GAIN)
        
        self.assertEqual(targets.calories, 2000)
        self.assertIsInstance(targets.protein_g, float)
        self.assertIsInstance(targets.carbs_g, float)
        self.assertIsInstance(targets.fat_g, float)
        self.assertGreater(targets.protein_g, 0)
        self.assertGreater(targets.carbs_g, 0)
        self.assertGreater(targets.fat_g, 0)
    
    def test_filter_recipes_by_diet(self):
        """Test recipe filtering by dietary preferences"""
        # Test omnivore diet
        omnivore_recipes = self.server._filter_recipes_by_diet(["omnivore"])
        self.assertGreater(len(omnivore_recipes), 0)
        
        # Test vegetarian diet
        vegetarian_recipes = self.server._filter_recipes_by_diet(["vegetarian"])
        self.assertGreater(len(vegetarian_recipes), 0)
        
        # Check that vegetarian recipes don't include meat
        for recipe in vegetarian_recipes:
            self.assertIn("vegetarian", recipe.diet_types)
    
    def test_select_best_recipe(self):
        """Test recipe selection based on calorie target"""
        recipes = list(self.server.sample_recipes.values())
        target_calories = 400
        
        best_recipe = self.server._select_best_recipe(recipes, target_calories)
        
        self.assertIsNotNone(best_recipe)
        # Should select recipe closest to target
        calorie_diff = abs(best_recipe.calories_per_serving - target_calories)
        
        # Verify it's actually the closest
        for recipe in recipes:
            other_diff = abs(recipe.calories_per_serving - target_calories)
            self.assertLessEqual(calorie_diff, other_diff)
    
    def test_get_optimized_meal_plan(self):
        """Test optimized meal plan generation"""
        async def run_test():
            result = await self.server.get_optimized_meal_plan(
                dietary_preferences=["omnivore"],
                calorie_target=2000,
                fitness_goals="muscle_gain",
                days=3
            )
            
            self.assertIsInstance(result, dict)
            self.assertIn("cached", result)
            self.assertIn("meal_plan", result)
            
            meal_plan = result["meal_plan"]
            self.assertIn("weekly_plan", meal_plan)
            self.assertIn("nutrition_targets", meal_plan)
            self.assertIn("nutrition_score", meal_plan)
            
            # Check that we have the right number of days
            self.assertEqual(len(meal_plan["weekly_plan"]), 3)
        
        asyncio.run(run_test())
    
    def test_meal_plan_caching(self):
        """Test that meal plans are properly cached"""
        async def run_test():
            # First call should not be cached
            result1 = await self.server.get_optimized_meal_plan(
                dietary_preferences=["vegetarian"],
                calorie_target=1800,
                fitness_goals="weight_loss",
                days=2
            )
            self.assertFalse(result1["cached"])
            
            # Second call with same parameters should be cached
            result2 = await self.server.get_optimized_meal_plan(
                dietary_preferences=["vegetarian"],
                calorie_target=1800,
                fitness_goals="weight_loss",
                days=2
            )
            self.assertTrue(result2["cached"])
            
            # Different parameters should not be cached
            result3 = await self.server.get_optimized_meal_plan(
                dietary_preferences=["vegan"],
                calorie_target=1800,
                fitness_goals="weight_loss",
                days=2
            )
            self.assertFalse(result3["cached"])
        
        asyncio.run(run_test())
    
    def test_analyze_nutrition_balance(self):
        """Test nutrition balance analysis"""
        async def run_test():
            # First generate a meal plan
            meal_plan_result = await self.server.get_optimized_meal_plan(
                dietary_preferences=["omnivore"],
                calorie_target=2000,
                fitness_goals="maintenance",
                days=2
            )
            
            # Then analyze it
            analysis = await self.server.analyze_nutrition_balance(meal_plan_result["meal_plan"])
            
            self.assertIsInstance(analysis, dict)
            self.assertIn("analysis_summary", analysis)
            self.assertIn("macronutrient_ratios", analysis)
            self.assertIn("balance_score", analysis)
            self.assertIn("warnings", analysis)
            self.assertIn("recommendations", analysis)
            
            # Check analysis summary structure
            summary = analysis["analysis_summary"]
            self.assertIn("avg_daily_calories", summary)
            self.assertIn("avg_daily_protein", summary)
            self.assertIn("avg_daily_carbs", summary)
            self.assertIn("avg_daily_fat", summary)
        
        asyncio.run(run_test())
    
    def test_get_recipe_suggestions(self):
        """Test recipe suggestions functionality"""
        async def run_test():
            result = await self.server.get_recipe_suggestions(
                calorie_range=(300, 500),
                dietary_preferences=["omnivore"],
                meal_type="any"
            )
            
            self.assertIsInstance(result, dict)
            self.assertIn("cached", result)
            self.assertIn("recipes", result)
            self.assertIn("count", result)
            
            # Check that returned recipes are within calorie range
            for recipe in result["recipes"]:
                calories = recipe["calories_per_serving"]
                self.assertGreaterEqual(calories, 300)
                self.assertLessEqual(calories, 500)
        
        asyncio.run(run_test())
    
    def test_optimize_meal_for_goals(self):
        """Test single meal optimization"""
        async def run_test():
            current_meal = {
                "calories_per_serving": 300,
                "protein_g": 10.0,
                "carbs_g": 40.0,
                "fat_g": 8.0
            }
            
            result = await self.server.optimize_meal_for_goals(
                current_meal=current_meal,
                fitness_goal="muscle_gain",
                target_calories=500
            )
            
            self.assertIsInstance(result, dict)
            self.assertIn("current_nutrition", result)
            self.assertIn("targets", result)
            self.assertIn("optimization_suggestions", result)
            self.assertIn("optimization_score", result)
            
            # Check that suggestions are provided
            self.assertIsInstance(result["optimization_suggestions"], list)
        
        asyncio.run(run_test())
    
    def test_get_cache_stats(self):
        """Test cache statistics functionality"""
        async def run_test():
            # Add some cache entries
            self.server._set_cache("test1", {"data": 1})
            self.server._set_cache("test2", {"data": 2})
            
            stats = await self.server.get_cache_stats()
            
            self.assertIsInstance(stats, dict)
            self.assertIn("total_entries", stats)
            self.assertIn("valid_entries", stats)
            self.assertIn("expired_entries", stats)
            self.assertIn("cache_hit_potential", stats)
            
            self.assertGreaterEqual(stats["total_entries"], 2)
        
        asyncio.run(run_test())
    
    def test_clear_cache(self):
        """Test cache clearing functionality"""
        async def run_test():
            # Add some cache entries
            self.server._set_cache("test_clear_1", {"data": 1})
            self.server._set_cache("test_clear_2", {"data": 2})
            self.server._set_cache("other_entry", {"data": 3})
            
            # Clear specific pattern
            result = await self.server.clear_cache("test_clear")
            self.assertEqual(result["cleared_entries"], 2)
            self.assertEqual(result["pattern"], "test_clear")
            
            # Verify specific entries were cleared
            self.assertIsNone(self.server._get_from_cache("test_clear_1"))
            self.assertIsNone(self.server._get_from_cache("test_clear_2"))
            # Other entry should still exist
            self.assertIsNotNone(self.server._get_from_cache("other_entry"))
            
            # Clear all
            result = await self.server.clear_cache()
            self.assertEqual(result["pattern"], "all")
            self.assertEqual(len(self.server.cache), 0)
        
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()