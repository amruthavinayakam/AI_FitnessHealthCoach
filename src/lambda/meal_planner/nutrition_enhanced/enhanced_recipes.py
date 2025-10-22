#!/usr/bin/env python3
"""
Enhanced Recipe Database for Multi-Source Nutrition Server

Comprehensive recipe collection using USDA nutrition data
"""

from multi_source_server import MealRecipe, NutritionFood
from typing import Dict


def create_enhanced_nutrition_db() -> Dict[str, NutritionFood]:
    """Create comprehensive nutrition database with USDA data"""
    return {
        # Proteins
        "chicken_breast": NutritionFood("Chicken Breast", 165, 31.0, 0, 3.6, 0, "usda"),
        "salmon": NutritionFood("Salmon", 208, 25.4, 0, 12.4, 0, "usda"),
        "tuna": NutritionFood("Tuna", 144, 30.0, 0, 1.0, 0, "usda"),
        "eggs": NutritionFood("Eggs", 155, 13.0, 1.1, 11.0, 0, "usda"),
        "greek_yogurt": NutritionFood("Greek Yogurt", 100, 10.0, 6.0, 5.0, 0, "usda"),
        "cottage_cheese": NutritionFood("Cottage Cheese", 98, 11.1, 3.4, 4.3, 0, "usda"),
        "tofu": NutritionFood("Tofu", 144, 17.3, 3.5, 8.7, 2.3, "usda"),
        "lentils": NutritionFood("Lentils", 116, 9.0, 20.0, 0.4, 7.9, "usda"),
        "black_beans": NutritionFood("Black Beans", 132, 8.9, 23.7, 0.5, 8.7, "usda"),
        "chickpeas": NutritionFood("Chickpeas", 164, 8.9, 27.4, 2.6, 7.6, "usda"),
        
        # Carbohydrates
        "brown_rice": NutritionFood("Brown Rice", 123, 2.6, 23.0, 0.9, 1.8, "usda"),
        "quinoa": NutritionFood("Quinoa", 222, 8.1, 39.4, 3.6, 2.8, "usda"),
        "oats": NutritionFood("Oats", 389, 16.9, 66.3, 6.9, 10.6, "usda"),
        "sweet_potato": NutritionFood("Sweet Potato", 86, 1.6, 20.1, 0.1, 3.0, "usda"),
        "banana": NutritionFood("Banana", 89, 1.1, 22.8, 0.3, 2.6, "usda"),
        "apple": NutritionFood("Apple", 52, 0.3, 13.8, 0.2, 2.4, "usda"),
        "berries": NutritionFood("Mixed Berries", 57, 0.7, 14.5, 0.3, 2.4, "usda"),
        "whole_wheat_bread": NutritionFood("Whole Wheat Bread", 247, 13.2, 41.0, 4.2, 6.0, "usda"),
        
        # Vegetables
        "broccoli": NutritionFood("Broccoli", 34, 2.8, 7.0, 0.4, 2.6, "usda"),
        "spinach": NutritionFood("Spinach", 23, 2.9, 3.6, 0.4, 2.2, "usda"),
        "kale": NutritionFood("Kale", 35, 2.9, 4.4, 1.5, 4.1, "usda"),
        "bell_pepper": NutritionFood("Bell Pepper", 31, 1.0, 7.3, 0.3, 2.5, "usda"),
        "tomato": NutritionFood("Tomato", 18, 0.9, 3.9, 0.2, 1.2, "usda"),
        "cucumber": NutritionFood("Cucumber", 16, 0.7, 4.0, 0.1, 0.5, "usda"),
        "carrots": NutritionFood("Carrots", 41, 0.9, 9.6, 0.2, 2.8, "usda"),
        "zucchini": NutritionFood("Zucchini", 17, 1.2, 3.1, 0.3, 1.0, "usda"),
        
        # Healthy Fats
        "avocado": NutritionFood("Avocado", 160, 2.0, 8.5, 14.7, 6.7, "usda"),
        "olive_oil": NutritionFood("Olive Oil", 884, 0, 0, 100.0, 0, "usda"),
        "almonds": NutritionFood("Almonds", 579, 21.2, 21.6, 49.9, 12.5, "usda"),
        "walnuts": NutritionFood("Walnuts", 654, 15.2, 13.7, 65.2, 6.7, "usda"),
        "chia_seeds": NutritionFood("Chia Seeds", 486, 16.5, 42.1, 30.7, 34.4, "usda"),
        "flax_seeds": NutritionFood("Flax Seeds", 534, 18.3, 28.9, 42.2, 27.3, "usda"),
        
        # Dairy & Alternatives
        "milk": NutritionFood("Milk", 61, 3.2, 4.8, 3.3, 0, "usda"),
        "almond_milk": NutritionFood("Almond Milk", 17, 0.6, 1.5, 1.1, 0.4, "usda"),
        "cheese": NutritionFood("Cheese", 402, 25.0, 1.3, 33.1, 0, "usda"),
    }


def create_enhanced_recipes(nutrition_db: Dict[str, NutritionFood]) -> Dict[str, MealRecipe]:
    """Create comprehensive recipe database"""
    recipes = {}
    
    # BREAKFAST RECIPES
    recipes["protein_oatmeal"] = MealRecipe(
        id="breakfast_001",
        name="High-Protein Oatmeal Bowl",
        ingredients=[
            {"food": nutrition_db["oats"], "amount_g": 50},
            {"food": nutrition_db["greek_yogurt"], "amount_g": 100},
            {"food": nutrition_db["berries"], "amount_g": 80},
            {"food": nutrition_db["chia_seeds"], "amount_g": 10},
            {"food": nutrition_db["almonds"], "amount_g": 15}
        ],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        prep_time_minutes=5,
        instructions=[
            "Cook oats with water or almond milk",
            "Mix in Greek yogurt while warm",
            "Top with fresh berries",
            "Sprinkle chia seeds and chopped almonds"
        ],
        meal_type="breakfast",
        diet_tags=["vegetarian", "high_protein", "high_fiber"]
    )
    
    recipes["veggie_scramble"] = MealRecipe(
        id="breakfast_002",
        name="Vegetable Scramble",
        ingredients=[
            {"food": nutrition_db["eggs"], "amount_g": 120},  # 2 eggs
            {"food": nutrition_db["spinach"], "amount_g": 50},
            {"food": nutrition_db["bell_pepper"], "amount_g": 60},
            {"food": nutrition_db["tomato"], "amount_g": 80},
            {"food": nutrition_db["avocado"], "amount_g": 50},
            {"food": nutrition_db["olive_oil"], "amount_g": 5}
        ],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        prep_time_minutes=10,
        instructions=[
            "Heat olive oil in pan",
            "Sauté bell peppers until soft",
            "Add spinach and tomatoes",
            "Scramble eggs with vegetables",
            "Serve with sliced avocado"
        ],
        meal_type="breakfast",
        diet_tags=["vegetarian", "low_carb", "high_protein"]
    )
    
    # LUNCH RECIPES
    recipes["chicken_quinoa_bowl"] = MealRecipe(
        id="lunch_001",
        name="Mediterranean Chicken Bowl",
        ingredients=[
            {"food": nutrition_db["chicken_breast"], "amount_g": 120},
            {"food": nutrition_db["quinoa"], "amount_g": 80},
            {"food": nutrition_db["cucumber"], "amount_g": 100},
            {"food": nutrition_db["tomato"], "amount_g": 100},
            {"food": nutrition_db["bell_pepper"], "amount_g": 80},
            {"food": nutrition_db["olive_oil"], "amount_g": 10}
        ],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        prep_time_minutes=25,
        instructions=[
            "Cook quinoa with vegetable broth",
            "Season and grill chicken breast",
            "Dice cucumber, tomatoes, and peppers",
            "Assemble bowl with quinoa base",
            "Top with chicken and vegetables",
            "Drizzle with olive oil and herbs"
        ],
        meal_type="lunch",
        diet_tags=["high_protein", "mediterranean", "balanced"]
    )
    
    recipes["salmon_sweet_potato"] = MealRecipe(
        id="lunch_002", 
        name="Baked Salmon with Sweet Potato",
        ingredients=[
            {"food": nutrition_db["salmon"], "amount_g": 120},
            {"food": nutrition_db["sweet_potato"], "amount_g": 200},
            {"food": nutrition_db["broccoli"], "amount_g": 150},
            {"food": nutrition_db["olive_oil"], "amount_g": 8}
        ],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        prep_time_minutes=30,
        instructions=[
            "Preheat oven to 400°F",
            "Cut sweet potato into cubes",
            "Toss sweet potato with half the olive oil",
            "Bake sweet potato for 20 minutes",
            "Season salmon and bake for 12-15 minutes",
            "Steam broccoli until tender",
            "Serve together with remaining olive oil"
        ],
        meal_type="lunch",
        diet_tags=["high_protein", "omega3", "balanced"]
    )
    
    # DINNER RECIPES  
    recipes["tofu_stir_fry"] = MealRecipe(
        id="dinner_001",
        name="Asian Tofu Stir Fry",
        ingredients=[
            {"food": nutrition_db["tofu"], "amount_g": 150},
            {"food": nutrition_db["brown_rice"], "amount_g": 80},
            {"food": nutrition_db["broccoli"], "amount_g": 100},
            {"food": nutrition_db["bell_pepper"], "amount_g": 80},
            {"food": nutrition_db["carrots"], "amount_g": 60},
            {"food": nutrition_db["olive_oil"], "amount_g": 10}
        ],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        prep_time_minutes=20,
        instructions=[
            "Cook brown rice according to package directions",
            "Press and cube tofu",
            "Heat oil in large pan or wok",
            "Stir-fry tofu until golden",
            "Add vegetables and stir-fry until crisp-tender",
            "Serve over brown rice"
        ],
        meal_type="dinner",
        diet_tags=["vegetarian", "vegan", "high_protein"]
    )
    
    recipes["lentil_curry"] = MealRecipe(
        id="dinner_002",
        name="Hearty Lentil Curry",
        ingredients=[
            {"food": nutrition_db["lentils"], "amount_g": 100},
            {"food": nutrition_db["brown_rice"], "amount_g": 70},
            {"food": nutrition_db["spinach"], "amount_g": 100},
            {"food": nutrition_db["tomato"], "amount_g": 150},
            {"food": nutrition_db["olive_oil"], "amount_g": 8}
        ],
        total_calories=0, total_protein=0, total_carbs=0, total_fat=0,
        prep_time_minutes=35,
        instructions=[
            "Cook lentils until tender",
            "Heat oil and sauté onions (not in nutrition calc)",
            "Add tomatoes and spices",
            "Simmer with cooked lentils",
            "Add spinach in last few minutes",
            "Serve over brown rice"
        ],
        meal_type="dinner",
        diet_tags=["vegetarian", "vegan", "high_fiber", "high_protein"]
    )
    
    return recipes