#!/usr/bin/env python3
"""
Fresh test with cache clearing to validate requirement 3.4
"""
import asyncio
import json
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp_servers', 'spoonacular_enhanced'))

from handler import MealPlannerService

async def test_fresh_nutrition_balance():
    """Test nutrition balance with fresh data (no cache)"""
    print("Testing fresh nutrition balance calculation...")
    
    meal_planner = MealPlannerService()
    
    # Clear cache first
    if meal_planner.mcp_server:
        await meal_planner.mcp_server.clear_cache()
        print("Cache cleared")
    
    user_profile = {
        'username': 'fresh_test_user',
        'user_id': 'fresh_test_123',
        'query': 'I need a balanced meal plan',
        'timestamp': 'fresh_test_timestamp'
    }
    
    try:
        result = await meal_planner.generate_meal_plan(
            user_profile=user_profile,
            dietary_preferences=['omnivore'],
            calorie_target=2000,
            fitness_goals='maintenance',
            days=7
        )
        
        print(f"Generated fresh meal plan (cached: {result.get('cached', False)})")
        
        # Examine the nutrition analysis
        analysis = result['nutrition_analysis']
        print(f"Analysis keys: {list(analysis.keys())}")
        
        if 'macronutrient_ratios' in analysis:
            ratios = analysis['macronutrient_ratios']
            print(f"Macronutrient ratios: {ratios}")
            
            protein_pct = ratios['protein_percent']
            carb_pct = ratios['carb_percent']
            fat_pct = ratios['fat_percent']
            
            print(f"Protein: {protein_pct}%")
            print(f"Carbs: {carb_pct}%")
            print(f"Fat: {fat_pct}%")
            print(f"Total: {protein_pct + carb_pct + fat_pct}%")
            
            # Check if within acceptable ranges
            protein_ok = 10 <= protein_pct <= 40
            carb_ok = 20 <= carb_pct <= 70
            fat_ok = 15 <= fat_pct <= 45
            
            print(f"Protein in range (10-40%): {protein_ok}")
            print(f"Carbs in range (20-70%): {carb_ok}")
            print(f"Fat in range (15-45%): {fat_ok}")
            
            if not carb_ok:
                # Let's examine the raw data
                meal_plan = result['meal_plan']
                weekly_plan = meal_plan.get('weekly_plan', [])
                
                print(f"\nExamining raw nutrition data for {len(weekly_plan)} days:")
                total_calories = 0
                total_protein = 0
                total_carbs = 0
                total_fat = 0
                
                for i, day_plan in enumerate(weekly_plan):
                    day_calories = day_plan.get('total_calories', 0)
                    day_protein = day_plan.get('total_protein', 0)
                    day_carbs = day_plan.get('total_carbs', 0)
                    day_fat = day_plan.get('total_fat', 0)
                    
                    print(f"Day {i+1}: {day_calories} cal, {day_protein:.1f}g protein, {day_carbs:.1f}g carbs, {day_fat:.1f}g fat")
                    
                    total_calories += day_calories
                    total_protein += day_protein
                    total_carbs += day_carbs
                    total_fat += day_fat
                
                avg_calories = total_calories / len(weekly_plan)
                avg_protein = total_protein / len(weekly_plan)
                avg_carbs = total_carbs / len(weekly_plan)
                avg_fat = total_fat / len(weekly_plan)
                
                print(f"\nAverages: {avg_calories:.1f} cal, {avg_protein:.1f}g protein, {avg_carbs:.1f}g carbs, {avg_fat:.1f}g fat")
                
                # Manual calculation
                protein_cal = avg_protein * 4
                carb_cal = avg_carbs * 4
                fat_cal = avg_fat * 9
                total_macro_cal = protein_cal + carb_cal + fat_cal
                
                manual_protein_pct = (protein_cal / total_macro_cal) * 100
                manual_carb_pct = (carb_cal / total_macro_cal) * 100
                manual_fat_pct = (fat_cal / total_macro_cal) * 100
                
                print(f"\nManual calculation:")
                print(f"Protein calories: {protein_cal:.1f} ({manual_protein_pct:.1f}%)")
                print(f"Carb calories: {carb_cal:.1f} ({manual_carb_pct:.1f}%)")
                print(f"Fat calories: {fat_cal:.1f} ({manual_fat_pct:.1f}%)")
                print(f"Total macro calories: {total_macro_cal:.1f}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_fresh_nutrition_balance()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)