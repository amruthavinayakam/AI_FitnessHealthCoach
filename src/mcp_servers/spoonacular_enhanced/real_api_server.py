#!/usr/bin/env python3
"""
Real Spoonacular API Integration for MCP Server

This version connects to the actual Spoonacular API for real meal planning data.
"""

import asyncio
import aiohttp
import hashlib
import json
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class FitnessGoal(Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    ENDURANCE = "endurance"


@dataclass
class RealRecipe:
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
    source_url: str
    image_url: str


@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl_seconds: int = 3600


class RealSpoonacularMCPServer:
    """
    MCP Server with real Spoonacular API integration
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SPOONACULAR_API_KEY')
        self.base_url = "https://api.spoonacular.com"
        self.cache = {}
        self.session = None
        
        # Rate limiting
        self.requests_per_day = 150  # Free tier limit
        self.requests_made = 0
        self.last_reset = time.time()
        
        if not self.api_key:
            print("⚠️ No Spoonacular API key found. Using demo mode.")
            self.demo_mode = True
        else:
            print(f"✅ Spoonacular API key configured: {self.api_key[:8]}...")
            self.demo_mode = False
    
    async def _get_session(self):
        """Get or create HTTP session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
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
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make another API request"""
        current_time = time.time()
        
        # Reset daily counter if it's a new day
        if current_time - self.last_reset > 86400:  # 24 hours
            self.requests_made = 0
            self.last_reset = current_time
        
        return self.requests_made < self.requests_per_day
    
    async def search_recipes(self, 
                           query: str = "",
                           diet: str = "",
                           max_calories: int = 800,
                           number: int = 10) -> List[RealRecipe]:
        """Search for recipes using Spoonacular API"""
        
        if self.demo_mode:
            return await self._get_demo_recipes(query, diet, max_calories, number)
        
        cache_key = self._generate_cache_key("search", query, diet, max_calories, number)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            print(f"📦 Cache hit for recipe search: {query}")
            return cached_data
        
        if not self._check_rate_limit():
            print("⚠️ Rate limit reached, using cached/demo data")
            return await self._get_demo_recipes(query, diet, max_calories, number)
        
        session = await self._get_session()
        
        params = {
            'apiKey': self.api_key,
            'query': query,
            'maxCalories': max_calories,
            'number': number,
            'addRecipeInformation': 'true',
            'addRecipeNutrition': 'true',
            'fillIngredients': 'true'
        }
        
        # Only add diet if specified
        if diet:
            params['diet'] = diet
        
        try:
            print(f"🌐 Making Spoonacular API call: search recipes for '{query}'")
            async with session.get(f"{self.base_url}/recipes/complexSearch", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    recipes = await self._parse_spoonacular_recipes(data.get('results', []))
                    
                    # Cache the results
                    self._set_cache(cache_key, recipes, ttl_seconds=1800)  # 30 minutes
                    self.requests_made += 1
                    
                    print(f"✅ Found {len(recipes)} recipes from Spoonacular API")
                    return recipes
                else:
                    print(f"❌ Spoonacular API error: {response.status}")
                    return await self._get_demo_recipes(query, diet, max_calories, number)
                    
        except Exception as e:
            print(f"❌ Error calling Spoonacular API: {e}")
            return await self._get_demo_recipes(query, diet, max_calories, number)
    
    async def _parse_spoonacular_recipes(self, api_results: List[Dict]) -> List[RealRecipe]:
        """Parse Spoonacular API results into our Recipe format"""
        recipes = []
        
        for result in api_results:
            try:
                # Extract nutrition info
                nutrition = result.get('nutrition', {})
                nutrients = {n['name']: n['amount'] for n in nutrition.get('nutrients', [])}
                
                # Extract ingredients
                ingredients = []
                for ingredient in result.get('extendedIngredients', []):
                    ingredients.append(ingredient.get('original', ''))
                
                # Extract instructions
                instructions = []
                for instruction in result.get('analyzedInstructions', []):
                    for step in instruction.get('steps', []):
                        instructions.append(step.get('step', ''))
                
                # Determine diet types
                diet_types = []
                if result.get('vegetarian'): diet_types.append('vegetarian')
                if result.get('vegan'): diet_types.append('vegan')
                if result.get('glutenFree'): diet_types.append('gluten_free')
                if result.get('dairyFree'): diet_types.append('dairy_free')
                
                recipe = RealRecipe(
                    id=result.get('id', 0),
                    title=result.get('title', 'Unknown Recipe'),
                    calories_per_serving=int(nutrients.get('Calories', 0)),
                    protein_g=float(nutrients.get('Protein', 0)),
                    carbs_g=float(nutrients.get('Carbohydrates', 0)),
                    fat_g=float(nutrients.get('Fat', 0)),
                    fiber_g=float(nutrients.get('Fiber', 0)),
                    prep_time_minutes=result.get('readyInMinutes', 30),
                    servings=result.get('servings', 1),
                    ingredients=ingredients[:10],  # Limit to 10 ingredients
                    instructions=instructions[:5],  # Limit to 5 steps
                    diet_types=diet_types,
                    source_url=result.get('sourceUrl', ''),
                    image_url=result.get('image', '')
                )
                
                recipes.append(recipe)
                
            except Exception as e:
                print(f"⚠️ Error parsing recipe: {e}")
                continue
        
        return recipes
    
    async def _get_demo_recipes(self, query: str, diet: str, max_calories: int, number: int) -> List[RealRecipe]:
        """Get demo recipes when API is not available"""
        demo_recipes = [
            RealRecipe(
                id=2001,
                title="Grilled Chicken Salad (Demo)",
                calories_per_serving=350,
                protein_g=30.0,
                carbs_g=15.0,
                fat_g=18.0,
                fiber_g=5.0,
                prep_time_minutes=20,
                servings=1,
                ingredients=["Chicken breast", "Mixed greens", "Cherry tomatoes", "Olive oil", "Lemon"],
                instructions=["Grill chicken", "Prepare salad", "Add dressing"],
                diet_types=["high_protein"],
                source_url="demo://recipe/2001",
                image_url="https://via.placeholder.com/300x200?text=Grilled+Chicken+Salad"
            ),
            RealRecipe(
                id=2002,
                title="Quinoa Buddha Bowl (Demo)",
                calories_per_serving=420,
                protein_g=15.0,
                carbs_g=65.0,
                fat_g=12.0,
                fiber_g=8.0,
                prep_time_minutes=25,
                servings=1,
                ingredients=["Quinoa", "Roasted vegetables", "Chickpeas", "Tahini", "Spinach"],
                instructions=["Cook quinoa", "Roast vegetables", "Assemble bowl"],
                diet_types=["vegetarian", "vegan"],
                source_url="demo://recipe/2002",
                image_url="https://via.placeholder.com/300x200?text=Quinoa+Buddha+Bowl"
            ),
            RealRecipe(
                id=2003,
                title="Salmon with Sweet Potato (Demo)",
                calories_per_serving=480,
                protein_g=35.0,
                carbs_g=40.0,
                fat_g=20.0,
                fiber_g=6.0,
                prep_time_minutes=30,
                servings=1,
                ingredients=["Salmon fillet", "Sweet potato", "Broccoli", "Olive oil", "Herbs"],
                instructions=["Bake salmon", "Roast sweet potato", "Steam broccoli"],
                diet_types=["high_protein", "omega3"],
                source_url="demo://recipe/2003",
                image_url="https://via.placeholder.com/300x200?text=Salmon+Sweet+Potato"
            )
        ]
        
        # Filter by diet if specified
        if diet:
            demo_recipes = [r for r in demo_recipes if diet.lower() in r.diet_types]
        
        # Filter by calories
        demo_recipes = [r for r in demo_recipes if r.calories_per_serving <= max_calories]
        
        return demo_recipes[:number]
    
    async def generate_meal_plan(self, 
                               target_calories: int = 2000,
                               fitness_goal: str = "maintenance",
                               diet_type: str = "",
                               days: int = 7) -> Dict[str, Any]:
        """Generate a real meal plan using Spoonacular API"""
        
        cache_key = self._generate_cache_key("meal_plan", target_calories, fitness_goal, diet_type, days)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            print(f"📦 Cache hit for meal plan: {target_calories} cal, {fitness_goal}")
            return {"cached": True, "meal_plan": cached_data}
        
        print(f"🍽️ Generating meal plan: {target_calories} calories, {fitness_goal} goal")
        
        # Calculate meal calorie distribution
        breakfast_calories = int(target_calories * 0.25)  # 25%
        lunch_calories = int(target_calories * 0.40)      # 40%
        dinner_calories = int(target_calories * 0.35)     # 35%
        
        weekly_plan = []
        
        for day in range(days):
            # Get recipes for each meal
            breakfast_recipes = await self.search_recipes(
                query="breakfast", 
                diet=diet_type, 
                max_calories=breakfast_calories + 50,
                number=3
            )
            
            lunch_recipes = await self.search_recipes(
                query="lunch main course", 
                diet=diet_type, 
                max_calories=lunch_calories + 100,
                number=3
            )
            
            dinner_recipes = await self.search_recipes(
                query="dinner main course", 
                diet=diet_type, 
                max_calories=dinner_calories + 100,
                number=3
            )
            
            # Select best recipes for the day
            breakfast = self._select_best_recipe(breakfast_recipes, breakfast_calories)
            lunch = self._select_best_recipe(lunch_recipes, lunch_calories)
            dinner = self._select_best_recipe(dinner_recipes, dinner_calories)
            
            daily_plan = {
                "day": f"Day {day + 1}",
                "breakfast": asdict(breakfast),
                "lunch": asdict(lunch),
                "dinner": asdict(dinner),
                "total_calories": breakfast.calories_per_serving + lunch.calories_per_serving + dinner.calories_per_serving,
                "total_protein": breakfast.protein_g + lunch.protein_g + dinner.protein_g,
                "total_carbs": breakfast.carbs_g + lunch.carbs_g + dinner.carbs_g,
                "total_fat": breakfast.fat_g + lunch.fat_g + dinner.fat_g
            }
            
            weekly_plan.append(daily_plan)
        
        # Calculate nutrition score
        avg_calories = sum(day["total_calories"] for day in weekly_plan) / days
        nutrition_score = max(0, 100 - abs(avg_calories - target_calories) / target_calories * 100)
        
        meal_plan = {
            "weekly_plan": weekly_plan,
            "target_calories": target_calories,
            "fitness_goal": fitness_goal,
            "diet_type": diet_type,
            "nutrition_score": nutrition_score,
            "api_requests_used": self.requests_made,
            "cache_enabled": True
        }
        
        # Cache the result
        self._set_cache(cache_key, meal_plan, ttl_seconds=3600)  # 1 hour
        
        return {"cached": False, "meal_plan": meal_plan}
    
    def _select_best_recipe(self, recipes: List[RealRecipe], target_calories: int) -> RealRecipe:
        """Select recipe closest to target calories"""
        if not recipes:
            # Fallback recipe
            return RealRecipe(
                id=9999,
                title="Simple Meal (Fallback)",
                calories_per_serving=target_calories,
                protein_g=target_calories * 0.15 / 4,  # 15% protein
                carbs_g=target_calories * 0.50 / 4,    # 50% carbs
                fat_g=target_calories * 0.35 / 9,      # 35% fat
                fiber_g=5.0,
                prep_time_minutes=15,
                servings=1,
                ingredients=["Basic ingredients"],
                instructions=["Simple preparation"],
                diet_types=["basic"],
                source_url="fallback://recipe",
                image_url="https://via.placeholder.com/300x200?text=Simple+Meal"
            )
        
        best_recipe = recipes[0]
        best_diff = abs(best_recipe.calories_per_serving - target_calories)
        
        for recipe in recipes:
            diff = abs(recipe.calories_per_serving - target_calories)
            if diff < best_diff:
                best_diff = diff
                best_recipe = recipe
        
        return best_recipe
    
    async def get_api_status(self) -> Dict[str, Any]:
        """Get API status and usage information"""
        return {
            "api_key_configured": not self.demo_mode,
            "demo_mode": self.demo_mode,
            "requests_made_today": self.requests_made,
            "requests_remaining": self.requests_per_day - self.requests_made,
            "cache_entries": len(self.cache),
            "rate_limit_status": "OK" if self._check_rate_limit() else "LIMIT_REACHED"
        }
    
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()


# Example usage and testing
async def main():
    """Test the real Spoonacular API integration"""
    # Get API key from environment variable
    api_key = os.getenv('SPOONACULAR_API_KEY')  # Set in .env file
    
    server = RealSpoonacularMCPServer(api_key=api_key)
    
    try:
        print("🧪 Testing Real Spoonacular MCP Server")
        print("=" * 50)
        
        # Test API status
        status = await server.get_api_status()
        print(f"📊 API Status: {json.dumps(status, indent=2)}")
        print()
        
        # Test recipe search
        print("🔍 Searching for healthy recipes...")
        recipes = await server.search_recipes(
            query="healthy chicken",
            diet="",
            max_calories=500,
            number=3
        )
        
        print(f"Found {len(recipes)} recipes:")
        for recipe in recipes:
            print(f"  - {recipe.title} ({recipe.calories_per_serving} cal)")
        print()
        
        # Test meal plan generation
        print("🍽️ Generating meal plan...")
        meal_plan_result = await server.generate_meal_plan(
            target_calories=1800,
            fitness_goal="weight_loss",
            diet_type="",
            days=3
        )
        
        meal_plan = meal_plan_result["meal_plan"]
        print(f"Generated {len(meal_plan['weekly_plan'])} day meal plan")
        print(f"Nutrition Score: {meal_plan['nutrition_score']:.1f}%")
        print(f"API Requests Used: {meal_plan['api_requests_used']}")
        
        # Show first day
        if meal_plan['weekly_plan']:
            day1 = meal_plan['weekly_plan'][0]
            print(f"\nDay 1 Sample:")
            print(f"  Breakfast: {day1['breakfast']['title']} ({day1['breakfast']['calories_per_serving']} cal)")
            print(f"  Lunch: {day1['lunch']['title']} ({day1['lunch']['calories_per_serving']} cal)")
            print(f"  Dinner: {day1['dinner']['title']} ({day1['dinner']['calories_per_serving']} cal)")
            print(f"  Total: {day1['total_calories']} calories")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())