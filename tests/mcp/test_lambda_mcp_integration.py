"""
Test Lambda MCP Server Integration

This test validates that Lambda functions can properly integrate with
the custom MCP servers for enhanced functionality.
"""

import asyncio
import json
import pytest
import sys
from pathlib import Path
from typing import Dict, Any


class TestLambdaMCPIntegration:
    """Test Lambda integration with custom MCP servers"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.mcp_config_file = self.project_root / "src" / "lambda" / "config" / "mcp_servers.json"
    
    def test_mcp_config_exists(self):
        """Test that MCP server configuration exists"""
        assert self.mcp_config_file.exists(), f"MCP config file not found: {self.mcp_config_file}"
        
        with open(self.mcp_config_file, 'r') as f:
            config = json.load(f)
        
        assert "MCP_SERVERS" in config
        assert "fitness_knowledge" in config["MCP_SERVERS"]
        assert "spoonacular_enhanced" in config["MCP_SERVERS"]
    
    def test_fitness_mcp_server_integration(self):
        """Test Fitness Knowledge MCP Server integration"""
        # Add server path
        server_path = self.project_root / "src" / "mcp_servers" / "fitness_knowledge"
        sys.path.insert(0, str(server_path))
        
        from server import FitnessKnowledgeMCPServer
        
        # Test server initialization
        server = FitnessKnowledgeMCPServer()
        assert server is not None
        assert len(server.exercise_db) > 0
        
        # Test exercise database
        assert "push_up" in server.exercise_db
        assert "squat" in server.exercise_db
        assert "deadlift" in server.exercise_db
    
    def test_spoonacular_mcp_server_integration(self):
        """Test Spoonacular Enhanced MCP Server integration"""
        # Clear previous imports
        if 'server' in sys.modules:
            del sys.modules['server']
        
        # Add server path
        server_path = self.project_root / "src" / "mcp_servers" / "spoonacular_enhanced"
        sys.path.insert(0, str(server_path))
        
        from server import SpoonacularEnhancedMCPServer
        
        # Test server initialization
        server = SpoonacularEnhancedMCPServer()
        assert server is not None
        assert len(server.sample_recipes) > 0
        
        # Test recipe database
        assert "oatmeal_berries" in server.sample_recipes
        assert "chicken_quinoa_bowl" in server.sample_recipes
    
    @pytest.mark.asyncio
    async def test_fitness_server_workout_generation_integration(self):
        """Test fitness server integration for workout generation"""
        # Add server path
        server_path = self.project_root / "src" / "mcp_servers" / "fitness_knowledge"
        sys.path.insert(0, str(server_path))
        
        from server import FitnessKnowledgeMCPServer
        
        server = FitnessKnowledgeMCPServer()
        
        # Test exercise info retrieval (simulating Bedrock integration)
        exercise_info = await server.get_exercise_info("push_up")
        
        assert exercise_info["name"] == "Push-up"
        assert "form_description" in exercise_info
        assert "safety_guidelines" in exercise_info
        assert len(exercise_info["safety_guidelines"]) > 0
        
        # Test workout progression (for progressive overload)
        progression = await server.suggest_workout_progression(
            {"exercises": ["push_up", "squat"]}, 
            "beginner"
        )
        
        assert "progression_recommendations" in progression
        assert "volume_adjustments" in progression
        assert "new_exercises" in progression
    
    @pytest.mark.asyncio
    async def test_spoonacular_server_meal_planning_integration(self):
        """Test Spoonacular server integration for meal planning"""
        # Clear previous imports
        if 'server' in sys.modules:
            del sys.modules['server']
        
        # Add server path
        server_path = self.project_root / "src" / "mcp_servers" / "spoonacular_enhanced"
        sys.path.insert(0, str(server_path))
        
        from server import SpoonacularEnhancedMCPServer
        
        server = SpoonacularEnhancedMCPServer()
        
        # Test meal plan generation (simulating Spoonacular API enhancement)
        meal_plan = await server.get_optimized_meal_plan(
            dietary_preferences=["omnivore"],
            calorie_target=2000,
            fitness_goals="muscle_gain",
            days=3
        )
        
        assert "meal_plan" in meal_plan
        assert "weekly_plan" in meal_plan["meal_plan"]
        assert len(meal_plan["meal_plan"]["weekly_plan"]) == 3
        
        # Test caching functionality
        cached_meal_plan = await server.get_optimized_meal_plan(
            dietary_preferences=["omnivore"],
            calorie_target=2000,
            fitness_goals="muscle_gain",
            days=3
        )
        
        assert cached_meal_plan["cached"] == True
        
        await server.close()
    
    @pytest.mark.asyncio
    async def test_workout_balance_validation(self):
        """Test workout balance validation for Lambda integration"""
        # Add server path
        server_path = self.project_root / "src" / "mcp_servers" / "fitness_knowledge"
        sys.path.insert(0, str(server_path))
        
        from server import FitnessKnowledgeMCPServer
        
        server = FitnessKnowledgeMCPServer()
        
        # Test balanced workout
        balanced_workout = {
            "exercises": ["push_up", "pull_up", "squat", "deadlift"]
        }
        
        balance_result = await server.validate_workout_balance(balanced_workout)
        
        assert "balanced" in balance_result
        assert "muscle_group_distribution" in balance_result
        assert "volume_distribution" in balance_result
        assert "warnings" in balance_result
        assert "recommendations" in balance_result
        
        # Test imbalanced workout
        imbalanced_workout = {
            "exercises": ["push_up", "bench_press", "overhead_press"]  # All pushing
        }
        
        imbalance_result = await server.validate_workout_balance(imbalanced_workout)
        
        assert len(imbalance_result["warnings"]) > 0
        assert len(imbalance_result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_nutrition_optimization(self):
        """Test nutrition optimization for Lambda integration"""
        # Clear previous imports
        if 'server' in sys.modules:
            del sys.modules['server']
        
        # Add server path
        server_path = self.project_root / "src" / "mcp_servers" / "spoonacular_enhanced"
        sys.path.insert(0, str(server_path))
        
        from server import SpoonacularEnhancedMCPServer
        
        server = SpoonacularEnhancedMCPServer()
        
        # Test nutrition analysis
        sample_meal_plan = {
            "weekly_plan": [
                {
                    "total_calories": 2000,
                    "total_protein": 150,
                    "total_carbs": 200,
                    "total_fat": 80
                },
                {
                    "total_calories": 1950,
                    "total_protein": 140,
                    "total_carbs": 210,
                    "total_fat": 75
                }
            ]
        }
        
        analysis = await server.analyze_nutrition_balance(sample_meal_plan)
        
        assert "analysis_summary" in analysis
        assert "macronutrient_ratios" in analysis
        assert "balance_score" in analysis
        assert "recommendations" in analysis
        
        # Validate macronutrient ratios
        ratios = analysis["macronutrient_ratios"]
        assert "protein_percent" in ratios
        assert "carb_percent" in ratios
        assert "fat_percent" in ratios
        
        # Ratios should add up to approximately 100%
        total_ratio = ratios["protein_percent"] + ratios["carb_percent"] + ratios["fat_percent"]
        assert 95 <= total_ratio <= 105  # Allow for rounding
        
        await server.close()
    
    def test_lambda_environment_configuration(self):
        """Test Lambda environment configuration for MCP servers"""
        with open(self.mcp_config_file, 'r') as f:
            config = json.load(f)
        
        mcp_servers = config["MCP_SERVERS"]
        
        # Validate fitness knowledge server config
        fitness_config = mcp_servers["fitness_knowledge"]
        assert "endpoint" in fitness_config
        assert "health_check" in fitness_config
        assert "timeout" in fitness_config
        assert fitness_config["timeout"] > 0
        
        # Validate Spoonacular server config
        spoonacular_config = mcp_servers["spoonacular_enhanced"]
        assert "endpoint" in spoonacular_config
        assert "health_check" in spoonacular_config
        assert "timeout" in spoonacular_config
        assert spoonacular_config["timeout"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """Test that MCP servers meet performance requirements"""
        import time
        
        # Test Fitness Knowledge Server performance
        server_path = self.project_root / "src" / "mcp_servers" / "fitness_knowledge"
        sys.path.insert(0, str(server_path))
        
        from server import FitnessKnowledgeMCPServer
        
        fitness_server = FitnessKnowledgeMCPServer()
        
        start_time = time.time()
        
        # Perform multiple operations
        await fitness_server.get_exercise_info("push_up")
        await fitness_server.suggest_workout_progression({"exercises": ["squat"]}, "beginner")
        await fitness_server.validate_workout_balance({"exercises": ["push_up", "squat"]})
        
        fitness_time = time.time() - start_time
        
        # Should complete within 1 second for development use
        assert fitness_time < 1.0, f"Fitness server too slow: {fitness_time:.3f}s"
        
        # Test Spoonacular Enhanced Server performance
        if 'server' in sys.modules:
            del sys.modules['server']
        
        server_path = self.project_root / "src" / "mcp_servers" / "spoonacular_enhanced"
        sys.path.insert(0, str(server_path))
        
        from server import SpoonacularEnhancedMCPServer
        
        spoonacular_server = SpoonacularEnhancedMCPServer()
        
        start_time = time.time()
        
        # Perform multiple operations
        meal_plan = await spoonacular_server.get_optimized_meal_plan(
            ["omnivore"], 2000, "maintenance", 1
        )
        await spoonacular_server.analyze_nutrition_balance(meal_plan["meal_plan"])
        
        spoonacular_time = time.time() - start_time
        
        # Should complete within 2 seconds for development use
        assert spoonacular_time < 2.0, f"Spoonacular server too slow: {spoonacular_time:.3f}s"
        
        await spoonacular_server.close()


if __name__ == "__main__":
    # Run basic validation without pytest
    test_instance = TestLambdaMCPIntegration()
    test_instance.setup_method()
    
    print("Testing Lambda MCP Integration...")
    
    try:
        test_instance.test_mcp_config_exists()
        print("✓ MCP configuration validation passed")
        
        test_instance.test_fitness_mcp_server_integration()
        print("✓ Fitness MCP server integration passed")
        
        test_instance.test_spoonacular_mcp_server_integration()
        print("✓ Spoonacular MCP server integration passed")
        
        # Run async tests
        async def run_async_tests():
            await test_instance.test_fitness_server_workout_generation_integration()
            print("✓ Fitness server workout generation integration passed")
            
            await test_instance.test_spoonacular_server_meal_planning_integration()
            print("✓ Spoonacular server meal planning integration passed")
            
            await test_instance.test_workout_balance_validation()
            print("✓ Workout balance validation passed")
            
            await test_instance.test_nutrition_optimization()
            print("✓ Nutrition optimization passed")
            
            await test_instance.test_performance_requirements()
            print("✓ Performance requirements passed")
        
        asyncio.run(run_async_tests())
        
        test_instance.test_lambda_environment_configuration()
        print("✓ Lambda environment configuration passed")
        
        print("\n✅ All Lambda MCP integration tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise