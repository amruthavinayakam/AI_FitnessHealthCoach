# Lambda function for meal plan generation using Spoonacular API and MCP server
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional

# Add the shared directory to the path for imports
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

try:
    from models import UserProfile, MealPlan, DailyMeals, Meal
    from logging_utils import (
        get_logger, log_api_request, log_function_call, 
        log_external_service_call, log_performance_metric
    )
except ImportError:
    # Fallback for local testing
    pass

# Initialize structured logger
logger = get_logger('meal-planner')

class MealPlannerService:
    """Service class for meal planning with MCP server integration"""
    
    def __init__(self):
        self.spoonacular_api_key = os.environ.get('SPOONACULAR_API_KEY')
        # In production, this would connect to the actual MCP server
        # For now, we'll simulate the MCP server functionality
        self.mcp_server = self._initialize_mcp_server()
    
    def _initialize_mcp_server(self):
        """Initialize connection to Spoonacular MCP server"""
        # Import the MCP server class
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp_servers', 'spoonacular_enhanced'))
            from server import SpoonacularEnhancedMCPServer
            return SpoonacularEnhancedMCPServer(api_key=self.spoonacular_api_key)
        except ImportError as e:
            logger.warning(f"Could not import MCP server: {e}. Using fallback implementation.")
            return None
    
    async def generate_meal_plan(self, 
                               user_profile: Dict[str, Any],
                               dietary_preferences: List[str],
                               calorie_target: int,
                               fitness_goals: str,
                               days: int = 7) -> Dict[str, Any]:
        """
        Generate optimized meal plan using MCP server with caching and optimization
        """
        try:
            if self.mcp_server:
                # Use MCP server for optimized meal planning with caching
                result = await self.mcp_server.get_optimized_meal_plan(
                    dietary_preferences=dietary_preferences,
                    calorie_target=calorie_target,
                    fitness_goals=fitness_goals,
                    days=days
                )
                
                meal_plan_data = result.get('meal_plan', {})
                
                # Add user context to the meal plan
                meal_plan_data['user_id'] = user_profile.get('user_id')
                meal_plan_data['username'] = user_profile.get('username')
                meal_plan_data['generated_at'] = user_profile.get('timestamp')
                
                # Perform nutritional analysis
                nutrition_analysis = await self.mcp_server.analyze_nutrition_balance(meal_plan_data)
                
                return {
                    'success': True,
                    'meal_plan': meal_plan_data,
                    'nutrition_analysis': nutrition_analysis,
                    'cached': result.get('cached', False),
                    'optimization_applied': True
                }
            else:
                # Fallback to basic meal planning without MCP server
                return await self._generate_basic_meal_plan(
                    user_profile, dietary_preferences, calorie_target, fitness_goals, days
                )
                
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            raise
    
    async def _generate_basic_meal_plan(self, 
                                      user_profile: Dict[str, Any],
                                      dietary_preferences: List[str],
                                      calorie_target: int,
                                      fitness_goals: str,
                                      days: int) -> Dict[str, Any]:
        """Fallback meal plan generation without MCP server"""
        # Basic meal plan structure
        daily_calorie_target = calorie_target
        
        # Simple meal distribution
        breakfast_calories = int(daily_calorie_target * 0.25)
        lunch_calories = int(daily_calorie_target * 0.40)
        dinner_calories = int(daily_calorie_target * 0.35)
        
        weekly_plan = []
        for day in range(days):
            day_plan = {
                "day": f"Day {day + 1}",
                "breakfast": {
                    "title": "Basic Breakfast",
                    "calories_per_serving": breakfast_calories,
                    "protein_g": breakfast_calories * 0.15 / 4,
                    "carbs_g": breakfast_calories * 0.55 / 4,
                    "fat_g": breakfast_calories * 0.30 / 9
                },
                "lunch": {
                    "title": "Basic Lunch",
                    "calories_per_serving": lunch_calories,
                    "protein_g": lunch_calories * 0.20 / 4,
                    "carbs_g": lunch_calories * 0.50 / 4,
                    "fat_g": lunch_calories * 0.30 / 9
                },
                "dinner": {
                    "title": "Basic Dinner",
                    "calories_per_serving": dinner_calories,
                    "protein_g": dinner_calories * 0.25 / 4,
                    "carbs_g": dinner_calories * 0.45 / 4,
                    "fat_g": dinner_calories * 0.30 / 9
                },
                "total_calories": daily_calorie_target,
                "total_protein": (breakfast_calories * 0.15 + lunch_calories * 0.20 + dinner_calories * 0.25) / 4,
                "total_carbs": (breakfast_calories * 0.55 + lunch_calories * 0.50 + dinner_calories * 0.45) / 4,
                "total_fat": (breakfast_calories * 0.30 + lunch_calories * 0.30 + dinner_calories * 0.30) / 9
            }
            weekly_plan.append(day_plan)
        
        return {
            'success': True,
            'meal_plan': {
                'weekly_plan': weekly_plan,
                'fitness_goal': fitness_goals,
                'dietary_preferences': dietary_preferences,
                'days': days,
                'user_id': user_profile.get('user_id'),
                'username': user_profile.get('username')
            },
            'nutrition_analysis': {
                'analysis_summary': {
                    'avg_daily_calories': daily_calorie_target,
                    'avg_daily_protein': daily_calorie_target * 0.20 / 4,
                    'avg_daily_carbs': daily_calorie_target * 0.50 / 4,
                    'avg_daily_fat': daily_calorie_target * 0.30 / 9
                },
                'balance_score': 75.0,
                'recommendations': ['Basic meal plan generated without optimization']
            },
            'cached': False,
            'optimization_applied': False
        }
    
    async def optimize_meal_for_goals(self, 
                                    current_meal: Dict[str, Any],
                                    fitness_goal: str,
                                    target_calories: int) -> Dict[str, Any]:
        """Optimize a single meal based on fitness goals using MCP server"""
        try:
            if self.mcp_server:
                return await self.mcp_server.optimize_meal_for_goals(
                    current_meal=current_meal,
                    fitness_goal=fitness_goal,
                    target_calories=target_calories
                )
            else:
                # Basic optimization without MCP server
                return {
                    'current_nutrition': current_meal,
                    'optimization_suggestions': ['MCP server not available for optimization'],
                    'optimization_score': 50.0
                }
        except Exception as e:
            logger.error(f"Error optimizing meal: {str(e)}")
            raise
    
    async def get_recipe_suggestions(self, 
                                   calorie_range: tuple,
                                   dietary_preferences: List[str],
                                   meal_type: str = "any") -> Dict[str, Any]:
        """Get recipe suggestions with dietary restriction handling"""
        try:
            if self.mcp_server:
                return await self.mcp_server.get_recipe_suggestions(
                    calorie_range=calorie_range,
                    dietary_preferences=dietary_preferences,
                    meal_type=meal_type
                )
            else:
                # Basic recipe suggestions without MCP server
                return {
                    'recipes': [],
                    'count': 0,
                    'message': 'MCP server not available for recipe suggestions'
                }
        except Exception as e:
            logger.error(f"Error getting recipe suggestions: {str(e)}")
            raise
    
    def _parse_dietary_preferences(self, query: str) -> List[str]:
        """Parse dietary preferences from user query"""
        preferences = []
        query_lower = query.lower()
        
        # Check for common dietary preferences
        if any(word in query_lower for word in ['vegetarian', 'veggie']):
            preferences.append('vegetarian')
        if any(word in query_lower for word in ['vegan', 'plant-based']):
            preferences.append('vegan')
        if any(word in query_lower for word in ['keto', 'ketogenic', 'low-carb']):
            preferences.append('ketogenic')
        if any(word in query_lower for word in ['paleo', 'paleolithic']):
            preferences.append('paleo')
        if any(word in query_lower for word in ['mediterranean']):
            preferences.append('mediterranean')
        
        # Default to omnivore if no specific diet mentioned
        if not preferences:
            preferences.append('omnivore')
        
        return preferences
    
    def _extract_calorie_target(self, query: str, fitness_goal: str) -> int:
        """Extract or estimate calorie target from user query and fitness goal"""
        # Look for explicit calorie mentions
        import re
        calorie_match = re.search(r'(\d{3,4})\s*(?:cal|calorie)', query.lower())
        if calorie_match:
            return int(calorie_match.group(1))
        
        # Default calorie targets based on fitness goals
        calorie_defaults = {
            'weight_loss': 1800,
            'muscle_gain': 2400,
            'maintenance': 2000,
            'endurance': 2200
        }
        
        return calorie_defaults.get(fitness_goal.lower(), 2000)
    
    def _extract_fitness_goal(self, query: str) -> str:
        """Extract fitness goal from user query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['lose weight', 'weight loss', 'cut', 'cutting']):
            return 'weight_loss'
        elif any(word in query_lower for word in ['gain muscle', 'build muscle', 'bulk', 'bulking']):
            return 'muscle_gain'
        elif any(word in query_lower for word in ['endurance', 'cardio', 'running', 'marathon']):
            return 'endurance'
        else:
            return 'maintenance'

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate meal plans using Spoonacular API and MCP server with optimization
    """
    try:
        # Parse the request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract user information
        username = body.get('username', 'anonymous')
        user_id = body.get('userId', 'unknown')
        query = body.get('query', '')
        
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Query is required'
                })
            }
        
        # Create user profile
        user_profile = {
            'username': username,
            'user_id': user_id,
            'query': query,
            'timestamp': context.aws_request_id if context else 'local-test'
        }
        
        # Initialize meal planner service
        meal_planner = MealPlannerService()
        
        # Extract parameters from query
        dietary_preferences = meal_planner._parse_dietary_preferences(query)
        fitness_goal = meal_planner._extract_fitness_goal(query)
        calorie_target = meal_planner._extract_calorie_target(query, fitness_goal)
        
        # Generate meal plan with MCP server optimization
        import asyncio
        
        async def generate_plan():
            return await meal_planner.generate_meal_plan(
                user_profile=user_profile,
                dietary_preferences=dietary_preferences,
                calorie_target=calorie_target,
                fitness_goals=fitness_goal,
                days=7
            )
        
        # Run the async function - handle existing event loop
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to use a different approach
                # This typically happens in testing environments
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, generate_plan())
                    result = future.result()
            else:
                result = loop.run_until_complete(generate_plan())
        except RuntimeError:
            # No event loop exists, create a new one
            result = asyncio.run(generate_plan())
        
        logger.info(f"Generated meal plan for user {username} with {len(dietary_preferences)} dietary preferences")
        logger.info(f"Calorie target: {calorie_target}, Fitness goal: {fitness_goal}")
        logger.info(f"MCP optimization applied: {result.get('optimization_applied', False)}")
        logger.info(f"Result cached: {result.get('cached', False)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'meal_plan': result['meal_plan'],
                    'nutrition_analysis': result['nutrition_analysis'],
                    'metadata': {
                        'dietary_preferences': dietary_preferences,
                        'fitness_goal': fitness_goal,
                        'calorie_target': calorie_target,
                        'optimization_applied': result.get('optimization_applied', False),
                        'cached': result.get('cached', False)
                    }
                },
                'message': 'Meal plan generated successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in meal planner: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }