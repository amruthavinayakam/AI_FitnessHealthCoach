#!/usr/bin/env python3
"""
Deploy Custom MCP Servers for Fitness Health Coach

This script handles the deployment of custom MCP servers for runtime use.
It configures the servers to be accessible by Lambda functions and tests
their performance and reliability.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

class MCPServerDeployer:
    """Handles deployment of custom MCP servers"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.mcp_servers_dir = self.project_root / "src" / "mcp_servers"
        self.deployment_config = {
            "fitness_knowledge": {
                "name": "fitness-knowledge-mcp",
                "path": self.mcp_servers_dir / "fitness_knowledge",
                "server_file": "server.py",
                "port": 8001,
                "health_endpoint": "/health"
            },
            "spoonacular_enhanced": {
                "name": "spoonacular-enhanced-mcp",
                "path": self.mcp_servers_dir / "spoonacular_enhanced", 
                "server_file": "server.py",
                "port": 8002,
                "health_endpoint": "/health"
            }
        }
    
    async def deploy_all_servers(self) -> Dict[str, Any]:
        """Deploy all custom MCP servers"""
        deployment_results = {}
        
        print("🚀 Starting MCP Server Deployment...")
        
        for server_name, config in self.deployment_config.items():
            print(f"\n📦 Deploying {server_name}...")
            
            try:
                result = await self.deploy_server(server_name, config)
                deployment_results[server_name] = result
                
                if result["success"]:
                    print(f"✅ {server_name} deployed successfully")
                else:
                    print(f"❌ {server_name} deployment failed: {result['error']}")
                    
            except Exception as e:
                print(f"❌ {server_name} deployment error: {e}")
                deployment_results[server_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return deployment_results
    
    async def deploy_server(self, server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a single MCP server"""
        server_path = config["path"]
        
        # Validate server files exist
        if not self.validate_server_files(server_path):
            return {
                "success": False,
                "error": f"Server files not found in {server_path}"
            }
        
        # Install dependencies
        deps_result = await self.install_dependencies(server_path)
        if not deps_result["success"]:
            return deps_result
        
        # Test server functionality
        test_result = await self.test_server_functionality(server_name, server_path)
        if not test_result["success"]:
            return test_result
        
        # Create deployment configuration
        config_result = self.create_deployment_config(server_name, config)
        if not config_result["success"]:
            return config_result
        
        return {
            "success": True,
            "server_name": server_name,
            "config": config,
            "deployment_time": time.time()
        }
    
    def validate_server_files(self, server_path: Path) -> bool:
        """Validate that required server files exist"""
        required_files = ["server.py", "requirements.txt"]
        
        for file_name in required_files:
            if not (server_path / file_name).exists():
                print(f"❌ Missing required file: {file_name}")
                return False
        
        return True
    
    async def install_dependencies(self, server_path: Path) -> Dict[str, Any]:
        """Install server dependencies"""
        requirements_file = server_path / "requirements.txt"
        
        try:
            print(f"📋 Installing dependencies from {requirements_file}")
            
            # Use pip to install requirements
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], capture_output=True, text=True, cwd=server_path)
            
            if result.returncode == 0:
                return {"success": True, "output": result.stdout}
            else:
                return {
                    "success": False,
                    "error": f"Dependency installation failed: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during dependency installation: {e}"
            }
    
    async def test_server_functionality(self, server_name: str, server_path: Path) -> Dict[str, Any]:
        """Test server functionality"""
        server_file = server_path / "server.py"
        
        try:
            print(f"🧪 Testing {server_name} functionality...")
            
            # Run the server's main function to test basic functionality
            result = subprocess.run([
                sys.executable, str(server_file)
            ], capture_output=True, text=True, cwd=server_path, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ {server_name} functionality test passed")
                return {
                    "success": True,
                    "test_output": result.stdout,
                    "test_time": time.time()
                }
            else:
                return {
                    "success": False,
                    "error": f"Functionality test failed: {result.stderr}",
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Server test timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during functionality test: {e}"
            }
    
    def create_deployment_config(self, server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create deployment configuration files"""
        try:
            # Create deployment directory
            deploy_dir = self.project_root / "deployment" / "mcp_servers"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            
            # Create server-specific config
            server_config = {
                "name": config["name"],
                "server_path": str(config["path"]),
                "server_file": config["server_file"],
                "port": config["port"],
                "health_endpoint": config["health_endpoint"],
                "deployment_time": time.time(),
                "status": "deployed"
            }
            
            config_file = deploy_dir / f"{server_name}_config.json"
            with open(config_file, 'w') as f:
                json.dump(server_config, f, indent=2)
            
            print(f"📝 Created deployment config: {config_file}")
            
            return {"success": True, "config_file": str(config_file)}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create deployment config: {e}"
            }
    
    async def test_server_performance(self, server_name: str) -> Dict[str, Any]:
        """Test MCP server performance and reliability"""
        print(f"⚡ Testing {server_name} performance...")
        
        # Import and test the specific server
        if server_name == "fitness_knowledge":
            return await self.test_fitness_server_performance()
        elif server_name == "spoonacular_enhanced":
            return await self.test_spoonacular_server_performance()
        else:
            return {"success": False, "error": f"Unknown server: {server_name}"}
    
    async def test_fitness_server_performance(self) -> Dict[str, Any]:
        """Test Fitness Knowledge MCP Server performance"""
        try:
            # Import the server
            sys.path.append(str(self.mcp_servers_dir / "fitness_knowledge"))
            from server import FitnessKnowledgeMCPServer
            
            server = FitnessKnowledgeMCPServer()
            
            # Performance tests
            start_time = time.time()
            
            # Test exercise info retrieval
            exercise_info = await server.get_exercise_info("push_up")
            
            # Test workout progression
            progression = await server.suggest_workout_progression(
                {"exercises": ["push_up", "squat"]}, "beginner"
            )
            
            # Test workout balance validation
            balance = await server.validate_workout_balance({
                "exercises": ["push_up", "pull_up", "squat"]
            })
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                "success": True,
                "response_time_seconds": response_time,
                "tests_completed": 3,
                "exercise_info_success": "name" in exercise_info,
                "progression_success": "progression_recommendations" in progression,
                "balance_success": "balanced" in balance
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Fitness server performance test failed: {e}"
            }
    
    async def test_spoonacular_server_performance(self) -> Dict[str, Any]:
        """Test Spoonacular Enhanced MCP Server performance"""
        try:
            # Import the server
            sys.path.append(str(self.mcp_servers_dir / "spoonacular_enhanced"))
            from server import SpoonacularEnhancedMCPServer
            
            server = SpoonacularEnhancedMCPServer()
            
            # Performance tests
            start_time = time.time()
            
            # Test meal plan generation
            meal_plan = await server.get_optimized_meal_plan(
                dietary_preferences=["omnivore"],
                calorie_target=2000,
                fitness_goals="maintenance",
                days=3
            )
            
            # Test nutrition analysis
            analysis = await server.analyze_nutrition_balance(meal_plan["meal_plan"])
            
            # Test recipe suggestions
            recipes = await server.get_recipe_suggestions(
                calorie_range=(300, 500),
                dietary_preferences=["vegetarian"]
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            await server.close()
            
            return {
                "success": True,
                "response_time_seconds": response_time,
                "tests_completed": 3,
                "meal_plan_success": "meal_plan" in meal_plan,
                "analysis_success": "analysis_summary" in analysis,
                "recipes_success": "recipes" in recipes,
                "cache_utilized": meal_plan.get("cached", False)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Spoonacular server performance test failed: {e}"
            }
    
    async def configure_lambda_integration(self) -> Dict[str, Any]:
        """Configure Lambda functions to connect to MCP servers"""
        print("🔗 Configuring Lambda integration with MCP servers...")
        
        try:
            # Create Lambda environment configuration
            lambda_config = {
                "MCP_SERVERS": {
                    "fitness_knowledge": {
                        "endpoint": "http://localhost:8001",
                        "health_check": "/health",
                        "timeout": 30
                    },
                    "spoonacular_enhanced": {
                        "endpoint": "http://localhost:8002", 
                        "health_check": "/health",
                        "timeout": 30
                    }
                }
            }
            
            # Save configuration for Lambda functions
            config_dir = self.project_root / "src" / "lambda" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / "mcp_servers.json"
            with open(config_file, 'w') as f:
                json.dump(lambda_config, f, indent=2)
            
            print(f"📝 Created Lambda MCP config: {config_file}")
            
            return {
                "success": True,
                "config_file": str(config_file),
                "servers_configured": len(lambda_config["MCP_SERVERS"])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lambda integration configuration failed: {e}"
            }
    
    async def generate_deployment_report(self, deployment_results: Dict[str, Any]) -> str:
        """Generate deployment report"""
        report_lines = [
            "# MCP Server Deployment Report",
            f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Deployment Summary"
        ]
        
        successful_deployments = sum(1 for result in deployment_results.values() if result.get("success", False))
        total_deployments = len(deployment_results)
        
        report_lines.extend([
            f"- Total servers: {total_deployments}",
            f"- Successful deployments: {successful_deployments}",
            f"- Failed deployments: {total_deployments - successful_deployments}",
            ""
        ])
        
        # Individual server results
        report_lines.append("## Individual Server Results")
        
        for server_name, result in deployment_results.items():
            status = "✅ SUCCESS" if result.get("success", False) else "❌ FAILED"
            report_lines.append(f"### {server_name} - {status}")
            
            if result.get("success", False):
                report_lines.extend([
                    f"- Deployment time: {time.strftime('%H:%M:%S', time.localtime(result.get('deployment_time', 0)))}",
                    f"- Configuration: {result.get('config', {}).get('name', 'N/A')}",
                    ""
                ])
            else:
                report_lines.extend([
                    f"- Error: {result.get('error', 'Unknown error')}",
                    ""
                ])
        
        # Performance test results
        report_lines.append("## Performance Test Results")
        
        for server_name in deployment_results.keys():
            if deployment_results[server_name].get("success", False):
                perf_result = await self.test_server_performance(server_name)
                
                if perf_result.get("success", False):
                    response_time = perf_result.get("response_time_seconds", 0)
                    tests_completed = perf_result.get("tests_completed", 0)
                    
                    report_lines.extend([
                        f"### {server_name}",
                        f"- Response time: {response_time:.3f} seconds",
                        f"- Tests completed: {tests_completed}",
                        f"- Status: ✅ PASSED",
                        ""
                    ])
                else:
                    report_lines.extend([
                        f"### {server_name}",
                        f"- Status: ❌ FAILED",
                        f"- Error: {perf_result.get('error', 'Unknown error')}",
                        ""
                    ])
        
        return "\n".join(report_lines)

async def main():
    """Main deployment function"""
    deployer = MCPServerDeployer()
    
    try:
        print("🎯 MCP Server Deployment Starting...")
        
        # Deploy all servers
        deployment_results = await deployer.deploy_all_servers()
        
        # Configure Lambda integration
        lambda_config = await deployer.configure_lambda_integration()
        
        # Generate and save deployment report
        report = await deployer.generate_deployment_report(deployment_results)
        
        report_file = Path("deployment_report.md")
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📊 Deployment report saved to: {report_file}")
        
        # Summary
        successful = sum(1 for r in deployment_results.values() if r.get("success", False))
        total = len(deployment_results)
        
        if successful == total:
            print(f"\n🎉 All {total} MCP servers deployed successfully!")
        else:
            print(f"\n⚠️  {successful}/{total} MCP servers deployed successfully")
        
        if lambda_config.get("success", False):
            print("✅ Lambda integration configured")
        else:
            print(f"❌ Lambda integration failed: {lambda_config.get('error', 'Unknown error')}")
        
        return deployment_results
        
    except Exception as e:
        print(f"❌ Deployment failed with error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    asyncio.run(main())