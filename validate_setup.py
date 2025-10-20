#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation script for Fitness Health Coach System setup
"""
import os
import subprocess
import sys

def check_command(command, description):
    """Check if a command is available"""
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True)
        print(f"✓ {description}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ {description}")
        return False

def check_file(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description}")
        return False

def main():
    """Main validation function"""
    print("🔍 Validating Fitness Health Coach System setup...\n")
    
    all_good = True
    
    # Check required commands
    print("Checking required tools:")
    all_good &= check_command("python --version", "Python is installed")
    all_good &= check_command("aws --version", "AWS CLI is installed")
    all_good &= check_command("cdk --version", "AWS CDK is installed")
    
    print("\nChecking AWS credentials:")
    all_good &= check_command("aws sts get-caller-identity", "AWS credentials are configured")
    
    print("\nChecking project structure:")
    required_files = [
        ("infrastructure/app.py", "CDK app file exists"),
        ("infrastructure/fitness_coach_stack.py", "CDK stack file exists"),
        ("src/lambda/fitness_coach_handler/handler.py", "Main handler exists"),
        ("src/lambda/workout_generator/handler.py", "Workout generator exists"),
        ("src/lambda/meal_planner/handler.py", "Meal planner exists"),
        ("cdk.json", "CDK configuration exists"),
        ("requirements.txt", "Requirements file exists")
    ]
    
    for filepath, description in required_files:
        all_good &= check_file(filepath, description)
    
    print("\nChecking MCP server files:")
    mcp_files = [
        ("src/mcp_servers/fitness_knowledge/server.py", "Fitness MCP server exists"),
        ("src/mcp_servers/spoonacular_enhanced/server.py", "Spoonacular MCP server exists"),
        (".kiro/settings/mcp.json", "MCP configuration exists")
    ]
    
    for filepath, description in mcp_files:
        all_good &= check_file(filepath, description)
    
    print(f"\n{'🎉 Setup validation passed!' if all_good else '❌ Setup validation failed!'}")
    
    if all_good:
        print("\nNext steps:")
        print("1. Run 'python deploy.py' to deploy the infrastructure")
        print("2. Configure your Spoonacular API key in AWS Secrets Manager")
        print("3. Test the API endpoints")
    else:
        print("\nPlease fix the issues above before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()