# Lambda function for meal plan generation using real APIs
import json
import logging
import os
import requests
import random
import time
from typing import Dict, Any, List

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class MealPlannerService:
    """Service class for meal planning using real APIs"""
    
    def __init__(self):
        self.spoonacular_api_key = os.environ.get('SPOONACULAR_API_KEY')
        self.usda_api_key = os.environ.get('USDA_API_KEY')
        self.edamam_app_id = os.environ.get('EDAMAM_APP_ID')
        self.edamam_app_key = os.environ.get('EDAMAM_APP_KEY')
        
        # Use Spoonacular if available, otherwise use Edamam
        self.use_spoonacular = bool(self.spoonacular_api_key)
        self.use_edamam = bool(self.edamam_app_id and self.edamam_app_key)
    
    def generate_meal_plan(self, user_profile: Dict[str, Any],
                           dietary_preferences: List[str],
                           calorie_target: int,
                           fitness_goals: str,
                           days: int = 7) -> Dict[str, Any]:
        """Generate meal plan using available APIs"""
        try:
            if self.use_spoonacular:
                return self._generate_spoonacular_meal_plan(
                    user_profile, dietary_preferences, calorie_target, fitness_goals, days
                )
            elif self.use_edamam:
                return self._generate_edamam_meal_plan(
                    user_profile, dietary_preferences, calorie_target, fitness_goals, days
                )
            else:
                return self._generate_enhanced_meal_plan(
                    user_profile, dietary_preferences, calorie_target, fitness_goals, days
                )
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return self._generate_enhanced_meal_plan(
                user_profile, dietary_preferences, calorie_target, fitness_goals, days
            )
    
    # ------------------------------------------------------------
    # 🥗 SPOONACULAR MEAL PLAN
    # ------------------------------------------------------------
    def _generate_spoonacular_meal_plan(self, user_profile, dietary_preferences, calorie_target, fitness_goals, days):
        """Generate meal plan using Spoonacular API"""
        try:
            url = "https://api.spoonacular.com/mealplanner/generate"
            diet_map = {
                'vegetarian': 'vegetarian', 'vegan': 'vegan',
                'ketogenic': 'ketogenic', 'paleo': 'paleo',
                'mediterranean': 'mediterranean'
            }
            diet = next((diet_map[p] for p in dietary_preferences if p in diet_map), None)

            params = {
                'apiKey': self.spoonacular_api_key,
                'timeFrame': 'week',
                'targetCalories': calorie_target
            }
            if diet:
                params['diet'] = diet

            logger.info(f"Calling Spoonacular API with params: {params}")
            
            for attempt in range(3):
                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt == 2:
                        raise
                    time.sleep(1)

            data = response.json()
            weekly_plan = []
            for day_name, meals in data.get('week', {}).items():
                weekly_plan.append({
                    "day": day_name.capitalize(),
                    "breakfast": self._format_spoonacular_meal(meals.get('meals', [{}])[0], 'breakfast'),
                    "lunch": self._format_spoonacular_meal(meals.get('meals', [{}])[1] if len(meals.get('meals', [])) > 1 else {}, 'lunch'),
                    "dinner": self._format_spoonacular_meal(meals.get('meals', [{}])[2] if len(meals.get('meals', [])) > 2 else {}, 'dinner'),
                    "total_calories": int(meals.get("nutrients", {}).get("calories", 0))
                })

            return {
                'success': True,
                'meal_plan': {
                    'weekly_plan': weekly_plan,
                    'fitness_goal': fitness_goals,
                    'dietary_preferences': dietary_preferences,
                    'days': days,
                    'user_id': user_profile.get('user_id'),
                    'username': user_profile.get('username'),
                    'api_source': 'spoonacular'
                },
                'nutrition_analysis': {
                    'analysis_summary': {
                        'avg_daily_calories': calorie_target,
                        'data_source': 'Spoonacular API'
                    },
                    'balance_score': 85.0,
                    'recommendations': ['Meal plan generated using Spoonacular API']
                },
                'cached': False,
                'optimization_applied': True
            }
        except Exception as e:
            logger.error(f"Spoonacular API error: {str(e)}")
            raise
    
    def _format_spoonacular_meal(self, meal_data: Dict[str, Any], meal_type: str) -> Dict[str, Any]:
        """Format Spoonacular meal data to our standard format"""
        return {
            'title': meal_data.get('title', f'{meal_type.capitalize()} Recipe'),
            'calories_per_serving': meal_data.get('calories', 0),
            'protein_g': meal_data.get('protein', 0),
            'carbs_g': meal_data.get('carbs', 0),
            'fat_g': meal_data.get('fat', 0),
            'ready_in_minutes': meal_data.get('readyInMinutes', 30),
            'servings': meal_data.get('servings', 1)
        }

    # ------------------------------------------------------------
    # 🥑 EDAMAM MEAL PLAN
    # ------------------------------------------------------------
    def _generate_edamam_meal_plan(self, user_profile, dietary_preferences, calorie_target, fitness_goals, days):
        """Generate meal plan using Edamam Recipe API"""
        try:
            health_labels = []
            if 'vegetarian' in dietary_preferences:
                health_labels.append('vegetarian')
            if 'vegan' in dietary_preferences:
                health_labels.append('vegan')
            if 'ketogenic' in dietary_preferences:
                health_labels.append('keto-friendly')
            if 'paleo' in dietary_preferences:
                health_labels.append('paleo')
            
            breakfast_cal = int(calorie_target * 0.25)
            lunch_cal = int(calorie_target * 0.40)
            dinner_cal = int(calorie_target * 0.35)
            
            weekly_plan = []
            for day in range(min(days, 7)):
                weekly_plan.append({
                    "day": f"Day {day + 1}",
                    "breakfast": self._get_edamam_recipe('breakfast', breakfast_cal, health_labels),
                    "lunch": self._get_edamam_recipe('lunch', lunch_cal, health_labels),
                    "dinner": self._get_edamam_recipe('dinner', dinner_cal, health_labels),
                    "total_calories": calorie_target
                })
            
            return {
                'success': True,
                'meal_plan': {
                    'weekly_plan': weekly_plan,
                    'fitness_goal': fitness_goals,
                    'dietary_preferences': dietary_preferences,
                    'days': days,
                    'user_id': user_profile.get('user_id'),
                    'username': user_profile.get('username'),
                    'api_source': 'edamam'
                },
                'nutrition_analysis': {
                    'analysis_summary': {
                        'avg_daily_calories': calorie_target,
                        'data_source': 'Edamam Recipe API'
                    },
                    'balance_score': 80.0,
                    'recommendations': ['Meal plan generated using Edamam Recipe API']
                },
                'cached': False,
                'optimization_applied': True
            }
        except Exception as e:
            logger.error(f"Edamam API error: {str(e)}")
            raise
    
    def _get_edamam_recipe(self, meal_type, target_calories, health_labels):
        """Get a single recipe from Edamam API"""
        try:
            params = {
                'type': 'public',
                'app_id': self.edamam_app_id,
                'app_key': self.edamam_app_key,
                'calories': f"{target_calories-100}-{target_calories+100}",
                'mealType': meal_type,
                'random': 'true'
            }
            if health_labels:
                params['health'] = health_labels[0]
            
            response = requests.get("https://api.edamam.com/api/recipes/v2", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('hits'):
                    recipe = data['hits'][0]['recipe']
                    nutrients = recipe.get('totalNutrients', {})
                    return {
                        'title': recipe.get('label', f'{meal_type.capitalize()} Recipe'),
                        'calories_per_serving': int(recipe.get('calories', target_calories) / recipe.get('yield', 1)),
                        'protein_g': round(nutrients.get('PROCNT', {}).get('quantity', 0) / recipe.get('yield', 1), 1),
                        'carbs_g': round(nutrients.get('CHOCDF', {}).get('quantity', 0) / recipe.get('yield', 1), 1),
                        'fat_g': round(nutrients.get('FAT', {}).get('quantity', 0) / recipe.get('yield', 1), 1),
                        'url': recipe.get('url'),
                        'image': recipe.get('image')
                    }
            return self._get_fallback_meal(meal_type, target_calories)
        except Exception as e:
            logger.warning(f"Edamam recipe fetch failed: {str(e)}")
            return self._get_fallback_meal(meal_type, target_calories)

    # ------------------------------------------------------------
    # 🥣 FALLBACK TEMPLATES
    # ------------------------------------------------------------
    def _generate_enhanced_meal_plan(self, user_profile, dietary_preferences, calorie_target, fitness_goals, days):
        """Enhanced fallback meal plan with variety"""
        meal_templates = {
            'breakfast': [
                {'name': 'Protein Oatmeal Bowl', 'protein_ratio': 0.20, 'carb_ratio': 0.60, 'fat_ratio': 0.20},
                {'name': 'Greek Yogurt Parfait', 'protein_ratio': 0.25, 'carb_ratio': 0.55, 'fat_ratio': 0.20},
                {'name': 'Scrambled Eggs with Toast', 'protein_ratio': 0.30, 'carb_ratio': 0.40, 'fat_ratio': 0.30},
                {'name': 'Protein Smoothie Bowl', 'protein_ratio': 0.25, 'carb_ratio': 0.50, 'fat_ratio': 0.25}
            ],
            'lunch': [
                {'name': 'Grilled Chicken Salad', 'protein_ratio': 0.35, 'carb_ratio': 0.35, 'fat_ratio': 0.30},
                {'name': 'Quinoa Power Bowl', 'protein_ratio': 0.25, 'carb_ratio': 0.50, 'fat_ratio': 0.25},
                {'name': 'Turkey Wrap', 'protein_ratio': 0.30, 'carb_ratio': 0.45, 'fat_ratio': 0.25},
                {'name': 'Salmon Rice Bowl', 'protein_ratio': 0.30, 'carb_ratio': 0.40, 'fat_ratio': 0.30}
            ],
            'dinner': [
                {'name': 'Lean Beef with Sweet Potato', 'protein_ratio': 0.35, 'carb_ratio': 0.35, 'fat_ratio': 0.30},
                {'name': 'Baked Chicken with Vegetables', 'protein_ratio': 0.40, 'carb_ratio': 0.30, 'fat_ratio': 0.30},
                {'name': 'Fish with Quinoa', 'protein_ratio': 0.35, 'carb_ratio': 0.35, 'fat_ratio': 0.30},
                {'name': 'Turkey Meatballs with Pasta', 'protein_ratio': 0.30, 'carb_ratio': 0.45, 'fat_ratio': 0.25}
            ]
        }
        if 'vegetarian' in dietary_preferences:
            meal_templates['lunch'].extend([
                {'name': 'Lentil Buddha Bowl', 'protein_ratio': 0.25, 'carb_ratio': 0.50, 'fat_ratio': 0.25},
                {'name': 'Chickpea Curry', 'protein_ratio': 0.20, 'carb_ratio': 0.55, 'fat_ratio': 0.25}
            ])
        
        breakfast_cal = int(calorie_target * 0.25)
        lunch_cal = int(calorie_target * 0.40)
        dinner_cal = int(calorie_target * 0.35)
        
        weekly_plan = []
        for day in range(days):
            weekly_plan.append({
                "day": f"Day {day + 1}",
                "breakfast": self._create_meal_from_template(random.choice(meal_templates['breakfast']), breakfast_cal),
                "lunch": self._create_meal_from_template(random.choice(meal_templates['lunch']), lunch_cal),
                "dinner": self._create_meal_from_template(random.choice(meal_templates['dinner']), dinner_cal),
                "total_calories": calorie_target
            })
        
        return {
            'success': True,
            'meal_plan': {
                'weekly_plan': weekly_plan,
                'fitness_goal': fitness_goals,
                'dietary_preferences': dietary_preferences,
                'days': days,
                'user_id': user_profile.get('user_id'),
                'username': user_profile.get('username'),
                'api_source': 'enhanced_fallback'
            },
            'nutrition_analysis': {
                'analysis_summary': {
                    'avg_daily_calories': calorie_target,
                    'data_source': 'Enhanced meal templates'
                },
                'balance_score': 75.0,
                'recommendations': ['Enhanced meal plan with variety and proper macronutrient distribution']
            },
            'cached': False,
            'optimization_applied': True
        }

    def _create_meal_from_template(self, template: Dict[str, Any], calories: int) -> Dict[str, Any]:
        protein_cal = calories * template['protein_ratio']
        carb_cal = calories * template['carb_ratio']
        fat_cal = calories * template['fat_ratio']
        return {
            'title': template['name'],
            'calories_per_serving': calories,
            'protein_g': round(protein_cal / 4, 1),
            'carbs_g': round(carb_cal / 4, 1),
            'fat_g': round(fat_cal / 9, 1),
            'template_based': True
        }

    def _get_fallback_meal(self, meal_type: str, calories: int) -> Dict[str, Any]:
        fallback_meals = {
            'breakfast': 'Oatmeal with Berries',
            'lunch': 'Chicken Salad',
            'dinner': 'Grilled Protein with Vegetables'
        }
        return {
            'title': fallback_meals.get(meal_type, f'{meal_type.capitalize()} Meal'),
            'calories_per_serving': calories,
            'protein_g': round(calories * 0.25 / 4, 1),
            'carbs_g': round(calories * 0.45 / 4, 1),
            'fat_g': round(calories * 0.30 / 9, 1),
            'fallback': True
        }

    # ------------------------------------------------------------
    # 🔍 TEXT PARSERS
    # ------------------------------------------------------------
    def _parse_dietary_preferences(self, query: str) -> List[str]:
        preferences = []
        query_lower = query.lower()
        if any(word in query_lower for word in ['vegetarian', 'veggie']):
            preferences.append('vegetarian')
        if any(word in query_lower for word in ['vegan', 'plant-based']):
            preferences.append('vegan')
        if any(word in query_lower for word in ['keto', 'ketogenic', 'low-carb']):
            preferences.append('ketogenic')
        if any(word in query_lower for word in ['paleo', 'paleolithic']):
            preferences.append('paleo')
        if 'mediterranean' in query_lower:
            preferences.append('mediterranean')
        if not preferences:
            preferences.append('omnivore')
        return preferences

    def _extract_calorie_target(self, query: str, fitness_goal: str) -> int:
        import re
        match = re.search(r'(\d{3,4})\s*(?:cal|calorie)', query.lower())
        if match:
            return int(match.group(1))
        defaults = {
            'weight_loss': 1800, 'muscle_gain': 2400,
            'maintenance': 2000, 'endurance': 2200
        }
        return defaults.get(fitness_goal.lower(), 2000)

    def _extract_fitness_goal(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ['lose weight', 'weight loss', 'cut', 'cutting']):
            return 'weight_loss'
        elif any(w in q for w in ['gain muscle', 'build muscle', 'bulk', 'bulking']):
            return 'muscle_gain'
        elif any(w in q for w in ['endurance', 'cardio', 'running', 'marathon']):
            return 'endurance'
        return 'maintenance'

# ------------------------------------------------------------
# 🚀 LAMBDA HANDLER
# ------------------------------------------------------------# ------------------------------------------------------------
# 🚀 LAMBDA HANDLER
# ------------------------------------------------------------
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
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

        # Build user profile metadata
        user_profile = {
            'username': username,
            'user_id': user_id,
            'query': query,
            'timestamp': getattr(context, 'aws_request_id', 'local-test')
        }

        # Initialize the planner service
        meal_planner = MealPlannerService()

        # Extract preferences and goals
        dietary_preferences = meal_planner._parse_dietary_preferences(query)
        fitness_goal = meal_planner._extract_fitness_goal(query)
        calorie_target = meal_planner._extract_calorie_target(query, fitness_goal)

        # Generate meal plan
        result = meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=dietary_preferences,
            calorie_target=calorie_target,
            fitness_goals=fitness_goal,
            days=7
        )

        logger.info(f"Generated meal plan for {username} ({fitness_goal}, {calorie_target} cal)")
        logger.info(f"API source: {result['meal_plan'].get('api_source')} | Cached: {result.get('cached')}")

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
                        'api_used': result['meal_plan'].get('api_source'),
                        'optimization_applied': result.get('optimization_applied', False),
                        'cached': result.get('cached', False)
                    }
                },
                'message': 'Meal plan generated successfully'
            })
        }

    except Exception as e:
        logger.error(f"Error in meal planner Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
