"""
Unit tests for Fitness Knowledge MCP Server
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the server module to path
sys.path.insert(0, os.path.dirname(__file__))
from server import FitnessKnowledgeMCPServer, DifficultyLevel, EquipmentType

class TestFitnessKnowledgeMCPServer(unittest.TestCase):
    """Test cases for Fitness Knowledge MCP Server"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = FitnessKnowledgeMCPServer()
    
    def test_exercise_database_initialization(self):
        """Test that exercise database is properly initialized"""
        self.assertIsInstance(self.server.exercise_db, dict)
        self.assertGreater(len(self.server.exercise_db), 0)
        
        # Check that push_up exercise exists and has required fields
        self.assertIn("push_up", self.server.exercise_db)
        push_up = self.server.exercise_db["push_up"]
        self.assertEqual(push_up.name, "Push-up")
        self.assertIsInstance(push_up.muscle_groups, list)
        self.assertIsInstance(push_up.safety_guidelines, list)
    
    def test_muscle_group_mapping_initialization(self):
        """Test muscle group mapping initialization"""
        self.assertIsInstance(self.server.muscle_group_mapping, dict)
        self.assertIn("push", self.server.muscle_group_mapping)
        self.assertIn("pull", self.server.muscle_group_mapping)
        self.assertIn("legs", self.server.muscle_group_mapping)
    
    def test_get_exercise_info_valid_exercise(self):
        """Test getting exercise info for valid exercise"""
        async def run_test():
            result = await self.server.get_exercise_info("push_up")
            
            self.assertIsInstance(result, dict)
            self.assertIn("name", result)
            self.assertIn("muscle_groups", result)
            self.assertIn("form_description", result)
            self.assertIn("safety_guidelines", result)
            self.assertEqual(result["name"], "Push-up")
        
        asyncio.run(run_test())
    
    def test_get_exercise_info_invalid_exercise(self):
        """Test getting exercise info for invalid exercise"""
        async def run_test():
            result = await self.server.get_exercise_info("nonexistent_exercise")
            
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)
            self.assertIn("not found", result["error"].lower())
        
        asyncio.run(run_test())
    
    def test_get_exercise_info_case_insensitive(self):
        """Test that exercise lookup is case insensitive"""
        async def run_test():
            result1 = await self.server.get_exercise_info("Push Up")
            result2 = await self.server.get_exercise_info("PUSH_UP")
            result3 = await self.server.get_exercise_info("push-up")
            
            # All should return the same exercise
            self.assertEqual(result1["name"], "Push-up")
            self.assertEqual(result2["name"], "Push-up")
            self.assertEqual(result3["name"], "Push-up")
        
        asyncio.run(run_test())
    
    def test_suggest_workout_progression_valid_level(self):
        """Test workout progression suggestions for valid user level"""
        async def run_test():
            current_plan = {"exercises": ["push_up", "squat"]}
            result = await self.server.suggest_workout_progression(current_plan, "beginner")
            
            self.assertIsInstance(result, dict)
            self.assertIn("progression_recommendations", result)
            self.assertIn("volume_adjustments", result)
            self.assertIn("new_exercises", result)
            self.assertIn("timeline", result)
        
        asyncio.run(run_test())
    
    def test_suggest_workout_progression_invalid_level(self):
        """Test workout progression with invalid user level"""
        async def run_test():
            current_plan = {"exercises": ["push_up"]}
            result = await self.server.suggest_workout_progression(current_plan, "invalid_level")
            
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)
        
        asyncio.run(run_test())
    
    def test_get_exercise_by_muscle_group(self):
        """Test getting exercises by muscle group"""
        async def run_test():
            result = await self.server.get_exercise_by_muscle_group("chest", "beginner")
            
            self.assertIsInstance(result, dict)
            self.assertIn("muscle_group", result)
            self.assertIn("exercises", result)
            self.assertIn("count", result)
            self.assertEqual(result["muscle_group"], "chest")
            self.assertIsInstance(result["exercises"], list)
        
        asyncio.run(run_test())
    
    def test_validate_workout_balance(self):
        """Test workout balance validation"""
        async def run_test():
            workout_plan = {"exercises": ["push_up", "pull_up", "squat"]}
            result = await self.server.validate_workout_balance(workout_plan)
            
            self.assertIsInstance(result, dict)
            self.assertIn("balanced", result)
            self.assertIn("muscle_group_distribution", result)
            self.assertIn("volume_distribution", result)
            self.assertIn("warnings", result)
            self.assertIn("recommendations", result)
            self.assertIsInstance(result["balanced"], bool)
        
        asyncio.run(run_test())
    
    def test_get_workout_safety_check(self):
        """Test workout safety check functionality"""
        async def run_test():
            exercises = ["push_up", "bench_press"]
            result = await self.server.get_workout_safety_check(exercises)
            
            self.assertIsInstance(result, dict)
            self.assertIn("safe", result)
            self.assertIn("safety_issues", result)
            self.assertIn("recommendations", result)
            self.assertIn("equipment_needed", result)
            self.assertIn("muscle_usage", result)
            self.assertIsInstance(result["safe"], bool)
        
        asyncio.run(run_test())
    
    def test_analyze_muscle_group_coverage(self):
        """Test muscle group coverage analysis"""
        exercises = ["push_up", "pull_up", "squat"]
        covered_groups = self.server._analyze_muscle_group_coverage(exercises)
        
        self.assertIsInstance(covered_groups, list)
        self.assertIn("chest", covered_groups)  # From push_up
        self.assertIn("lats", covered_groups)   # From pull_up
        self.assertIn("quadriceps", covered_groups)  # From squat
    
    def test_identify_missing_muscle_groups(self):
        """Test identification of missing muscle groups"""
        covered_groups = ["chest", "quadriceps"]
        missing_groups = self.server._identify_missing_muscle_groups(covered_groups)
        
        self.assertIsInstance(missing_groups, list)
        # Should identify missing essential groups
        essential_missing = ["lats", "shoulders", "hamstrings", "glutes"]
        for group in essential_missing:
            if group not in covered_groups:
                self.assertIn(group, missing_groups)

if __name__ == "__main__":
    unittest.main()