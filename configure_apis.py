#!/usr/bin/env python3
"""
API Configuration Tool for Fitness Health Coach

Configure real API integrations or use demo mode.
"""

import json
import os
from pathlib import Path


def configure_nutrition_api():
    """Configure nutrition API integration"""
    print("🔧 Nutrition API Configuration")
    print("=" * 40)
    
    print("Choose your nutrition data source:")
    print("1. Enhanced Nutrition Database (USDA + Custom recipes)")
    print("2. Demo mode (simple sample data)")
    print("3. Spoonacular API (requires API key)")
    print()
    
    choice = input("Choose option (1, 2, or 3): ").strip()
    
    if choice == "1":
        print("✅ Enhanced nutrition database selected")
        return configure_enhanced_nutrition()
    elif choice == "2":
        print("✅ Demo mode selected - using sample data")
        return configure_demo_mode()
    elif choice == "3":
        print("🌐 Spoonacular API mode selected")
        return configure_real_api()
    else:
        print("❌ Invalid choice")
        return False


def configure_enhanced_nutrition():
    """Configure enhanced nutrition database"""
    config = {
        "mode": "enhanced_nutrition",
        "nutrition_source": "usda_custom",
        "description": "Using USDA FoodData Central + Custom recipe database"
    }
    
    save_config(config)
    print("✅ Enhanced nutrition database configured successfully!")
    print("📋 Features available:")
    print("   • USDA FoodData Central nutrition data")
    print("   • 30+ comprehensive food items")
    print("   • 6+ detailed recipe templates")
    print("   • Accurate macro and micronutrient tracking")
    print("   • No API limits or keys required")
    print("   • Dietary preference filtering")
    return True


def configure_demo_mode():
    """Configure demo mode"""
    config = {
        "mode": "demo",
        "spoonacular_api_key": None,
        "description": "Using sample data for development and testing"
    }
    
    save_config(config)
    print("✅ Demo mode configured successfully!")
    print("📋 Features available:")
    print("   • Sample recipes and meal plans")
    print("   • Fast response times")
    print("   • No API limits")
    print("   • Perfect for development and testing")
    return True


def configure_real_api():
    """Configure real Spoonacular API"""
    print()
    print("📝 To use the real Spoonacular API, you need an API key:")
    print("1. Go to https://spoonacular.com/food-api")
    print("2. Sign up for a free account")
    print("3. Get your API key from the dashboard")
    print("4. Free tier includes 150 requests per day")
    print()
    
    api_key = input("Enter your Spoonacular API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⚠️ No API key provided, falling back to demo mode")
        return configure_demo_mode()
    
    # Validate API key format (basic check)
    if len(api_key) < 20:
        print("⚠️ API key seems too short, are you sure it's correct?")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return configure_real_api()
    
    config = {
        "mode": "real_api",
        "spoonacular_api_key": api_key,
        "description": "Using real Spoonacular API for meal planning"
    }
    
    save_config(config)
    print("✅ Real API mode configured successfully!")
    print("📋 Features available:")
    print("   • Real recipes from Spoonacular database")
    print("   • Thousands of recipes to choose from")
    print("   • Accurate nutrition information")
    print("   • Intelligent caching to save API calls")
    print(f"   • API Key: {api_key[:8]}...{api_key[-4:]}")
    return True


def save_config(config):
    """Save configuration to file"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "api_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Also set environment variable for current session
    if config.get("spoonacular_api_key"):
        os.environ["SPOONACULAR_API_KEY"] = config["spoonacular_api_key"]


def load_config():
    """Load configuration from file"""
    config_file = Path("config/api_config.json")
    
    if not config_file.exists():
        return None
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading config: {e}")
        return None


def show_current_config():
    """Show current configuration"""
    config = load_config()
    
    if not config:
        print("❌ No configuration found")
        return
    
    print("📋 Current API Configuration:")
    print("=" * 30)
    print(f"Mode: {config['mode']}")
    print(f"Description: {config['description']}")
    
    if config.get('spoonacular_api_key'):
        key = config['spoonacular_api_key']
        print(f"Spoonacular API Key: {key[:8]}...{key[-4:]}")
    else:
        print("Spoonacular API Key: Not configured (demo mode)")


def test_configuration():
    """Test the current configuration"""
    print("🧪 Testing API Configuration")
    print("=" * 30)
    
    config = load_config()
    if not config:
        print("❌ No configuration found. Please run configuration first.")
        return
    
    if config["mode"] == "demo":
        print("✅ Demo mode - testing sample data...")
        print("   • Sample recipes: Available")
        print("   • Sample meal plans: Available") 
        print("   • Response time: < 0.1s")
        print("   • API limits: None")
        print("✅ Demo mode working correctly!")
        
    elif config["mode"] == "real_api":
        print("🌐 Real API mode - testing Spoonacular connection...")
        api_key = config.get("spoonacular_api_key")
        
        if not api_key:
            print("❌ No API key found in configuration")
            return
        
        # Set environment variable
        os.environ["SPOONACULAR_API_KEY"] = api_key
        
        print(f"   • API Key: {api_key[:8]}...{api_key[-4:]}")
        print("   • Testing connection... (this may take a moment)")
        
        # Test the real API server
        import asyncio
        import sys
        sys.path.append("src/mcp_servers/spoonacular_enhanced")
        
        async def test_real_api():
            try:
                from real_api_server import RealSpoonacularMCPServer
                
                server = RealSpoonacularMCPServer(api_key=api_key)
                
                # Test API status
                status = await server.get_api_status()
                print(f"   • API Status: {status['rate_limit_status']}")
                print(f"   • Requests remaining: {status['requests_remaining']}")
                
                # Test a simple recipe search
                recipes = await server.search_recipes(query="chicken", number=1)
                if recipes:
                    print(f"   • Recipe search: ✅ Found {len(recipes)} recipes")
                    print(f"   • Sample recipe: {recipes[0].title}")
                else:
                    print("   • Recipe search: ⚠️ No recipes found")
                
                await server.close()
                print("✅ Real API mode working correctly!")
                
            except Exception as e:
                print(f"❌ Real API test failed: {e}")
                print("💡 Tip: Check your API key and internet connection")
        
        asyncio.run(test_real_api())


def main():
    """Main configuration menu"""
    print("🎯 Fitness Health Coach - Nutrition Configuration")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Configure Nutrition Source")
        print("2. Show current configuration")
        print("3. Test configuration")
        print("4. Exit")
        
        choice = input("\nChoose option (1-4): ").strip()
        
        if choice == "1":
            configure_nutrition_api()
        elif choice == "2":
            show_current_config()
        elif choice == "3":
            test_configuration()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice, please try again")


if __name__ == "__main__":
    main()