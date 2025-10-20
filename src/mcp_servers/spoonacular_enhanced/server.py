# Custom Spoonacular MCP Server with caching and optimization
import asyncio
import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
# import aiohttp  # Optional for production Spoonacular API integration

class FitnessGoal(Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    ENDURANCE = "endurance"

class DietType(Enum):
    OMNIVORE = "omnivore"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    KETO = "ketogenic"
    PALEO = "paleo"
    MEDITERRANEAN = "mediterranean"

@dataclass
class NutritionTarget:
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float

@dataclass
class Recipe:
    id: int
    title: str
    calories_per_serving: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    prep_time_minutes: int
    servings: int
    ingredients: List[str]
    instructions: List[str]
    diet_types: List[str]

@dataclass
class MealPlan:
    day: str
    breakfast: Recipe
    lunch: Recipe
    dinner: Recipe
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    nutrition_score: float

@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl_seconds: int = 3600  # 1 hour default

class SpoonacularEnhancedMCPServer:
    """
    MCP Server providing enhanced Spoonacular API integration with caching and optimization
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.cache = {}  # In-memory cache for development, Redis for production
        self.api_key = api_key
        self.base_url = "https://api.spoonacular.com"
        self.session = None
        
        # Nutrition optimization parameters - more conservative multipliers
        self.fitness_goal_multipliers = {
            FitnessGoal.WEIGHT_LOSS: {"protein": 1.15, "carbs": 0.85, "fat": 0.95},
            FitnessGoal.MUSCLE_GAIN: {"protein": 1.3, "carbs": 1.1, "fat": 1.0},
            FitnessGoal.MAINTENANCE: {"protein": 1.0, "carbs": 1.0, "fat": 1.0},
            FitnessGoal.ENDURANCE: {"protein": 1.05, "carbs": 1.15, "fat": 0.95}
        }
        
        # DEPRECATED: This server is replaced by Enhanced Nutrition Database
        # Use src/mcp_servers/nutrition_enhanced/multi_source_server.py instead
        self.sample_recipes = self._initialize_sample_recipes()
    
    def _initialize_sample_recipes(self) -> Dict[str, Recipe]:
        """Initialize sample recipe database for development and testing"""
        return {
            "oatmeal_berries": Recipe(
                id=1001,
                title="Overnight Oats with Berries",
                calories_per_serving=320,
                protein_g=12.0,
                carbs_g=58.0,
                fat_g=6.0,
                fiber_g=8.0,
                prep_time_minutes=10,
                servings=1,
                ingredients=["1/2 cup rolled oats", "1/2 cup milk", "1/4 cup mixed berries", "1 tbsp honey"],
                instructions=["Mix oats and milk", "Add berries and honey", "Refrigerate overnight"],
                diet_types=["vegetarian"]
            ),
            "chicken_quinoa_bowl": Recipe(
                id=1002,
                title="Grilled Chicken Quinoa Bowl",
                calories_per_serving=450,
                protein_g=35.0,
                carbs_g=40.0,
                fat_g=15.0,
                fiber_g=6.0,
                prep_time_minutes=25,
                servings=1,
                ingredients=["4oz chicken breast", "1/2 cup quinoa", "mixed vegetables", "olive oil"],
                instructions=["Grill chicken", "Cook quinoa", "Sauté vegetables", "Combine in bowl"],
                diet_types=["omnivore", "high_protein"]
            ),
            "salmon_sweet_potato": Recipe(
                id=1003,
                title="Baked Salmon with Sweet Potato",
                calories_per_serving=520,
                protein_g=40.0,
                carbs_g=35.0,
                fat_g=22.0,
                fiber_g=5.0,
                prep_time_minutes=30,
                servings=1,
                ingredients=["5oz salmon fillet", "1 medium sweet potato", "asparagus", "lemon"],
                instructions=["Bake salmon at 400F", "Roast sweet potato", "Steam asparagus"],
                diet_types=["omnivore", "high_protein", "omega3"]
            ),
            "veggie_stir_fry": Recipe(
                id=1004,
                title="Tofu Vegetable Stir Fry",
                calories_per_serving=380,
                protein_g=18.0,
                carbs_g=45.0,
                fat_g=12.0,
                fiber_g=7.0,
                prep_time_minutes=20,
                servings=1,
                ingredients=["4oz firm tofu", "mixed vegetables", "brown rice", "soy sauce"],
                instructions=["Press and cube tofu", "Stir fry vegetables", "Serve over rice"],
                diet_types=["vegetarian", "vegan"]
            )
        }
    
    async def _get_session(self):
        """Get or create HTTP session - placeholder for aiohttp integration"""
        # In production, this would return aiohttp.ClientSession()
        return None
    
    def _generate_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_string = "_".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: CacheEntry) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry.timestamp < cache_entry.ttl_seconds
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if self._is_cache_valid(entry):
                return entry.data
            else:
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl_seconds: int = 3600):
        """Set data in cache with TTL"""
        self.cache[cache_key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds
        )
    
    def _calculate_nutrition_targets(self, calorie_target: int, fitness_goal: FitnessGoal) -> NutritionTarget:
        """Calculate optimal nutrition targets based on fitness goals"""
        multipliers = self.fitness_goal_multipliers[fitness_goal]
        
        # Base macronutrient distribution (45% carbs, 25% protein, 30% fat)
        # Adjusted for better balance within acceptable ranges
        base_protein_calories = calorie_target * 0.25
        base_carb_calories = calorie_target * 0.45
        base_fat_calories = calorie_target * 0.30
        
        # Apply fitness goal multipliers
        protein_calories = base_protein_calories * multipliers["protein"]
        carb_calories = base_carb_calories * multipliers["carbs"]
        fat_calories = base_fat_calories * multipliers["fat"]
        
        # Normalize to maintain calorie target and ensure balanced ratios
        total_adjusted = protein_calories + carb_calories + fat_calories
        normalization_factor = calorie_target / total_adjusted
        
        protein_calories *= normalization_factor
        carb_calories *= normalization_factor
        fat_calories *= normalization_factor
        
        # Ensure ratios stay within acceptable ranges
        protein_ratio = protein_calories / calorie_target
        carb_ratio = carb_calories / calorie_target
        fat_ratio = fat_calories / calorie_target
        
        # Adjust if ratios are out of acceptable ranges
        if carb_ratio > 0.65:  # Max 65% carbs
            excess = carb_calories - (calorie_target * 0.65)
            carb_calories = calorie_target * 0.65
            # Redistribute excess to protein and fat
            protein_calories += excess * 0.6
            fat_calories += excess * 0.4
        
        if protein_ratio < 0.15:  # Min 15% protein
            deficit = (calorie_target * 0.15) - protein_calories
            protein_calories = calorie_target * 0.15
            # Take from carbs primarily
            carb_calories -= deficit * 0.8
            fat_calories -= deficit * 0.2
        
        return NutritionTarget(
            calories=calorie_target,
            protein_g=protein_calories / 4,  # 4 calories per gram
            carbs_g=carb_calories / 4,
            fat_g=fat_calories / 9,  # 9 calories per gram
            fiber_g=calorie_target / 1000 * 14  # 14g fiber per 1000 calories
        )
    
    async def get_optimized_meal_plan(self, 
                                    dietary_preferences: List[str],
                                    calorie_target: int,
                                    fitness_goals: str,
                                    days: int = 7) -> Dict[str, Any]:
        """Generate optimized meal plan with caching"""
        cache_key = self._generate_cache_key(
            sorted(dietary_preferences), calorie_target, fitness_goals, days
        )
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return {
                "cached": True,
                "meal_plan": cached_data,
                "cache_key": cache_key
            }
        
        # Generate new meal plan
        try:
            fitness_goal = FitnessGoal(fitness_goals.lower())
        except ValueError:
            fitness_goal = FitnessGoal.MAINTENANCE
        
        meal_plan = await self._generate_optimized_plan(
            dietary_preferences, calorie_target, fitness_goal, days
        )
        
        # Cache the result
        self._set_cache(cache_key, meal_plan, ttl_seconds=7200)  # 2 hours
        
        return {
            "cached": False,
            "meal_plan": meal_plan,
            "cache_key": cache_key
        }
    
    async def _generate_optimized_plan(self, 
                                     dietary_preferences: List[str],
                                     calorie_target: int,
                                     fitness_goal: FitnessGoal,
                                     days: int) -> Dict[str, Any]:
        """Generate optimized meal plan using sample recipes or Spoonacular API"""
        nutrition_targets = self._calculate_nutrition_targets(calorie_target, fitness_goal)
        daily_calorie_target = calorie_target // 3  # Distribute across 3 meals
        
        # Filter recipes based on dietary preferences
        suitable_recipes = self._filter_recipes_by_diet(dietary_preferences)
        
        weekly_plan = []
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}
        
        for day in range(days):
            daily_plan = await self._generate_daily_meal_plan(
                suitable_recipes, daily_calorie_target, nutrition_targets
            )
            weekly_plan.append(daily_plan)
            
            # Accumulate nutrition totals
            total_nutrition["calories"] += daily_plan["total_calories"]
            total_nutrition["protein"] += daily_plan["total_protein"]
            total_nutrition["carbs"] += daily_plan["total_carbs"]
            total_nutrition["fat"] += daily_plan["total_fat"]
        
        # Calculate nutrition score
        nutrition_score = self._calculate_nutrition_score(total_nutrition, nutrition_targets, days)
        
        return {
            "weekly_plan": weekly_plan,
            "nutrition_targets": asdict(nutrition_targets),
            "actual_nutrition": total_nutrition,
            "nutrition_score": nutrition_score,
            "fitness_goal": fitness_goal.value,
            "dietary_preferences": dietary_preferences,
            "days": days
        }
    
    def _filter_recipes_by_diet(self, dietary_preferences: List[str]) -> List[Recipe]:
        """Filter recipes based on dietary preferences"""
        suitable_recipes = []
        
        for recipe in self.sample_recipes.values():
            # Check if recipe matches dietary preferences
            if not dietary_preferences or "omnivore" in dietary_preferences:
                suitable_recipes.append(recipe)
            elif any(pref.lower() in recipe.diet_types for pref in dietary_preferences):
                suitable_recipes.append(recipe)
        
        return suitable_recipes if suitable_recipes else list(self.sample_recipes.values())
    
    async def _generate_daily_meal_plan(self, 
                                      suitable_recipes: List[Recipe],
                                      daily_calorie_target: int,
                                      nutrition_targets: NutritionTarget) -> Dict[str, Any]:
        """Generate a single day meal plan"""
        # Simple meal distribution: 25% breakfast, 40% lunch, 35% dinner
        breakfast_calories = int(daily_calorie_target * 0.25)
        lunch_calories = int(daily_calorie_target * 0.40)
        dinner_calories = int(daily_calorie_target * 0.35)
        
        # Select recipes closest to calorie targets
        breakfast = self._select_best_recipe(suitable_recipes, breakfast_calories)
        lunch = self._select_best_recipe(suitable_recipes, lunch_calories)
        dinner = self._select_best_recipe(suitable_recipes, dinner_calories)
        
        total_calories = breakfast.calories_per_serving + lunch.calories_per_serving + dinner.calories_per_serving
        total_protein = breakfast.protein_g + lunch.protein_g + dinner.protein_g
        total_carbs = breakfast.carbs_g + lunch.carbs_g + dinner.carbs_g
        total_fat = breakfast.fat_g + lunch.fat_g + dinner.fat_g
        
        return {
            "breakfast": asdict(breakfast),
            "lunch": asdict(lunch),
            "dinner": asdict(dinner),
            "total_calories": total_calories,
            "total_protein": total_protein,
            "total_carbs": total_carbs,
            "total_fat": total_fat
        }
    
    def _select_best_recipe(self, recipes: List[Recipe], target_calories: int) -> Recipe:
        """Select recipe closest to target calories"""
        if not recipes:
            return self.sample_recipes["oatmeal_berries"]  # Fallback
        
        best_recipe = recipes[0]
        best_diff = abs(best_recipe.calories_per_serving - target_calories)
        
        for recipe in recipes:
            diff = abs(recipe.calories_per_serving - target_calories)
            if diff < best_diff:
                best_diff = diff
                best_recipe = recipe
        
        return best_recipe
    
    def _calculate_nutrition_score(self, actual: Dict, targets: NutritionTarget, days: int) -> float:
        """Calculate nutrition score based on how close actual matches targets"""
        daily_targets = {
            "calories": targets.calories,
            "protein": targets.protein_g,
            "carbs": targets.carbs_g,
            "fat": targets.fat_g
        }
        
        daily_actual = {k: v / days for k, v in actual.items() if k != "fiber"}
        
        scores = []
        for nutrient in ["calories", "protein", "carbs", "fat"]:
            target = daily_targets[nutrient]
            actual_val = daily_actual[nutrient]
            
            if target > 0:
                ratio = actual_val / target
                # Score is higher when closer to 1.0 (perfect match)
                score = max(0, 1 - abs(1 - ratio))
                scores.append(score)
        
        return sum(scores) / len(scores) * 100  # Convert to percentage
    
    async def analyze_nutrition_balance(self, meal_plan: Dict) -> Dict[str, Any]:
        """Analyze nutritional balance and suggest improvements"""
        weekly_plan = meal_plan.get("weekly_plan", [])
        if not weekly_plan:
            return {"error": "No meal plan data provided"}
        
        # Aggregate nutrition data
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        daily_averages = []
        
        for day_plan in weekly_plan:
            daily_nutrition = {
                "calories": day_plan.get("total_calories", 0),
                "protein": day_plan.get("total_protein", 0),
                "carbs": day_plan.get("total_carbs", 0),
                "fat": day_plan.get("total_fat", 0)
            }
            daily_averages.append(daily_nutrition)
            
            for nutrient, value in daily_nutrition.items():
                total_nutrition[nutrient] += value
        
        days = len(weekly_plan)
        avg_daily = {k: v / days for k, v in total_nutrition.items()}
        
        # Analyze macronutrient ratios - ensure they're calculated correctly
        total_calories = avg_daily["calories"]
        if total_calories > 0:
            protein_calories = avg_daily["protein"] * 4
            carb_calories = avg_daily["carbs"] * 4
            fat_calories = avg_daily["fat"] * 9
            
            # Calculate actual calorie contribution
            actual_total_calories = protein_calories + carb_calories + fat_calories
            
            # Use actual total for ratio calculation to avoid discrepancies
            if actual_total_calories > 0:
                protein_ratio = protein_calories / actual_total_calories
                carb_ratio = carb_calories / actual_total_calories
                fat_ratio = fat_calories / actual_total_calories
            else:
                protein_ratio = carb_ratio = fat_ratio = 0
        else:
            protein_ratio = carb_ratio = fat_ratio = 0
        
        # Generate recommendations
        recommendations = []
        warnings = []
        
        if protein_ratio < 0.15:
            warnings.append("Protein intake may be too low")
            recommendations.append("Consider adding more protein-rich foods like lean meats, fish, or legumes")
        elif protein_ratio > 0.35:
            warnings.append("Protein intake may be too high")
            recommendations.append("Consider balancing with more carbohydrates and healthy fats")
        
        if carb_ratio < 0.30:
            recommendations.append("Consider adding more complex carbohydrates for energy")
        elif carb_ratio > 0.60:
            recommendations.append("Consider reducing refined carbohydrates")
        
        if fat_ratio < 0.20:
            recommendations.append("Add healthy fats like avocados, nuts, or olive oil")
        elif fat_ratio > 0.40:
            recommendations.append("Consider reducing saturated fat intake")
        
        return {
            "analysis_summary": {
                "avg_daily_calories": round(avg_daily["calories"]),
                "avg_daily_protein": round(avg_daily["protein"], 1),
                "avg_daily_carbs": round(avg_daily["carbs"], 1),
                "avg_daily_fat": round(avg_daily["fat"], 1)
            },
            "macronutrient_ratios": {
                "protein_percent": round(protein_ratio * 100, 1),
                "carb_percent": round(carb_ratio * 100, 1),
                "fat_percent": round(fat_ratio * 100, 1)
            },
            "balance_score": meal_plan.get("nutrition_score", 0),
            "warnings": warnings,
            "recommendations": recommendations,
            "daily_variation": daily_averages
        }

    async def get_recipe_suggestions(self, 
                                   calorie_range: Tuple[int, int],
                                   dietary_preferences: List[str],
                                   meal_type: str = "any") -> Dict[str, Any]:
        """Get recipe suggestions based on criteria"""
        cache_key = self._generate_cache_key(calorie_range, dietary_preferences, meal_type)
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return {"cached": True, "recipes": cached_data}
        
        suitable_recipes = self._filter_recipes_by_diet(dietary_preferences)
        min_cal, max_cal = calorie_range
        
        filtered_recipes = [
            recipe for recipe in suitable_recipes
            if min_cal <= recipe.calories_per_serving <= max_cal
        ]
        
        recipe_data = [asdict(recipe) for recipe in filtered_recipes]
        self._set_cache(cache_key, recipe_data, ttl_seconds=1800)  # 30 minutes
        
        return {
            "cached": False,
            "recipes": recipe_data,
            "count": len(recipe_data),
            "calorie_range": calorie_range,
            "dietary_preferences": dietary_preferences
        }
    
    async def optimize_meal_for_goals(self, 
                                    current_meal: Dict,
                                    fitness_goal: str,
                                    target_calories: int) -> Dict[str, Any]:
        """Optimize a single meal based on fitness goals"""
        try:
            goal = FitnessGoal(fitness_goal.lower())
        except ValueError:
            goal = FitnessGoal.MAINTENANCE
        
        nutrition_targets = self._calculate_nutrition_targets(target_calories, goal)
        
        # Calculate current meal nutrition
        current_nutrition = {
            "calories": current_meal.get("calories_per_serving", 0),
            "protein": current_meal.get("protein_g", 0),
            "carbs": current_meal.get("carbs_g", 0),
            "fat": current_meal.get("fat_g", 0)
        }
        
        # Calculate optimization suggestions
        suggestions = []
        
        # Protein optimization
        protein_target = nutrition_targets.protein_g / 3  # Assuming 3 meals per day
        if current_nutrition["protein"] < protein_target * 0.8:
            suggestions.append({
                "type": "increase_protein",
                "current": current_nutrition["protein"],
                "target": protein_target,
                "suggestion": "Add protein-rich ingredients like lean meat, fish, eggs, or legumes"
            })
        
        # Calorie optimization
        if current_nutrition["calories"] > target_calories * 1.2:
            suggestions.append({
                "type": "reduce_calories",
                "current": current_nutrition["calories"],
                "target": target_calories,
                "suggestion": "Consider smaller portions or lower-calorie alternatives"
            })
        elif current_nutrition["calories"] < target_calories * 0.8:
            suggestions.append({
                "type": "increase_calories",
                "current": current_nutrition["calories"],
                "target": target_calories,
                "suggestion": "Add healthy fats or complex carbohydrates"
            })
        
        return {
            "current_nutrition": current_nutrition,
            "targets": {
                "calories": target_calories,
                "protein": protein_target,
                "carbs": nutrition_targets.carbs_g / 3,
                "fat": nutrition_targets.fat_g / 3
            },
            "fitness_goal": goal.value,
            "optimization_suggestions": suggestions,
            "optimization_score": self._calculate_meal_score(current_nutrition, nutrition_targets, target_calories)
        }
    
    def _calculate_meal_score(self, current: Dict, targets: NutritionTarget, target_calories: int) -> float:
        """Calculate how well a meal matches nutritional targets"""
        meal_targets = {
            "calories": target_calories,
            "protein": targets.protein_g / 3,
            "carbs": targets.carbs_g / 3,
            "fat": targets.fat_g / 3
        }
        
        scores = []
        for nutrient in ["calories", "protein", "carbs", "fat"]:
            target = meal_targets[nutrient]
            actual = current.get(nutrient, 0)
            
            if target > 0:
                ratio = actual / target
                score = max(0, 1 - abs(1 - ratio))
                scores.append(score)
        
        return sum(scores) / len(scores) * 100
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        total_entries = len(self.cache)
        valid_entries = sum(1 for entry in self.cache.values() if self._is_cache_valid(entry))
        expired_entries = total_entries - valid_entries
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_hit_potential": f"{(valid_entries/max(total_entries, 1)*100):.1f}%"
        }
    
    async def clear_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Clear cache entries, optionally matching a pattern"""
        if pattern is None:
            cleared_count = len(self.cache)
            self.cache.clear()
            return {"cleared_entries": cleared_count, "pattern": "all"}
        
        cleared_count = 0
        keys_to_remove = []
        
        for key in self.cache.keys():
            if pattern in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
            cleared_count += 1
        
        return {"cleared_entries": cleared_count, "pattern": pattern}
    
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

# MCP Server Protocol Integration
async def main():
    """Main function to run the MCP server"""
    server = SpoonacularEnhancedMCPServer()
    
    try:
        print("Spoonacular Enhanced MCP Server initialized")
        print(f"Sample recipe database contains {len(server.sample_recipes)} recipes")
        
        # Test functionality
        test_meal_plan = await server.get_optimized_meal_plan(
            dietary_preferences=["omnivore"],
            calorie_target=2000,
            fitness_goals="muscle_gain",
            days=3
        )
        
        print(f"Generated meal plan for 3 days")
        print(f"Nutrition score: {test_meal_plan['meal_plan']['nutrition_score']:.1f}%")
        
        # Test nutrition analysis
        analysis = await server.analyze_nutrition_balance(test_meal_plan['meal_plan'])
        print(f"Average daily calories: {analysis['analysis_summary']['avg_daily_calories']}")
        
        # Test cache stats
        cache_stats = await server.get_cache_stats()
        print(f"Cache entries: {cache_stats['total_entries']}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        await server.close()

if __name__ == "__main__":
    asyncio.run(main())