#!/usr/bin/env python3
"""
Test Real API vs Demo Mode

This script demonstrates the difference between using real Spoonacular API
and demo mode with sample data.
"""

import asyncio
import json
import requests
import time


def test_local_server_modes():
    """Test both demo and real API modes through local server"""
    print("🧪 Testing Real API vs Demo Mode")
    print("=" * 50)
    
    # Test nutrition planning endpoint
    test_url = "http://localhost:8080/api/nutrition"
    
    print("1. Testing current configuration...")
    try:
        response = requests.get(f"{test_url}?goal=weight_loss&calories=1800", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            mode = data.get("mode", "unknown")
            server_type = data.get("mcp_server", "unknown")
            
            print(f"✅ Server Response: {response.status_code}")
            print(f"🔧 Mode: {mode}")
            print(f"🖥️ MCP Server: {server_type}")
            print(f"⏱️ Response Time: {data.get('response_time', 'N/A')}")
            print(f"💾 Cached: {data.get('cached', False)}")
            
            # Show meal plan details
            meal_plan = data.get("meal_plan", {})
            if isinstance(meal_plan, dict) and "meal_plan" in meal_plan:
                plan_data = meal_plan["meal_plan"]
                if "weekly_plan" in plan_data and plan_data["weekly_plan"]:
                    day1 = plan_data["weekly_plan"][0]
                    print(f"\n📋 Sample Day Menu:")
                    print(f"   Breakfast: {day1.get('breakfast', {}).get('title', 'N/A')}")
                    print(f"   Lunch: {day1.get('lunch', {}).get('title', 'N/A')}")
                    print(f"   Dinner: {day1.get('dinner', {}).get('title', 'N/A')}")
                    print(f"   Total Calories: {day1.get('total_calories', 'N/A')}")
            
            print()
            
            if mode == "real_api":
                print("🌐 REAL API MODE ACTIVE!")
                print("   • Using actual Spoonacular API")
                print("   • Real recipes from database")
                print("   • API rate limiting in effect")
                print("   • Intelligent caching enabled")
            else:
                print("🧪 DEMO MODE ACTIVE!")
                print("   • Using sample data")
                print("   • Hardcoded recipes")
                print("   • No API limits")
                print("   • Fast response times")
            
        else:
            print(f"❌ Server Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to localhost:8080")
        print("💡 Make sure the local server is running: py local_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")


def show_configuration_options():
    """Show how to configure different modes"""
    print("\n🔧 Configuration Options")
    print("=" * 30)
    
    print("To switch between modes:")
    print("1. Run: py configure_apis.py")
    print("2. Choose option 1 (Configure APIs)")
    print("3. Select:")
    print("   • Option 1: Demo mode (sample data)")
    print("   • Option 2: Real API (requires Spoonacular API key)")
    print()
    
    print("📝 To get a Spoonacular API key:")
    print("1. Visit: https://spoonacular.com/food-api")
    print("2. Sign up for free account")
    print("3. Get API key from dashboard")
    print("4. Free tier: 150 requests/day")
    print()
    
    print("🎯 Benefits of Real API:")
    print("   • Thousands of real recipes")
    print("   • Accurate nutrition data")
    print("   • Dietary restrictions support")
    print("   • Fresh meal variety")
    print()
    
    print("🧪 Benefits of Demo Mode:")
    print("   • No API key needed")
    print("   • Unlimited requests")
    print("   • Fast development")
    print("   • Consistent test data")


def main():
    """Main test function"""
    print("🎯 Fitness Health Coach - API Mode Testing")
    print("=" * 60)
    
    # Test current server configuration
    test_local_server_modes()
    
    # Show configuration options
    show_configuration_options()
    
    print("\n🚀 Next Steps:")
    print("1. Visit http://localhost:8080 to test interactively")
    print("2. Try the 'Test Nutrition Planning MCP' button")
    print("3. Send chat messages like 'make me a nutrition plan for weight loss'")
    print("4. Use py configure_apis.py to switch between modes")
    
    print(f"\n📊 Current Status: Server running on localhost:8080")


if __name__ == "__main__":
    main()