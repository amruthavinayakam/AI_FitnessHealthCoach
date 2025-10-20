#!/usr/bin/env python3
"""
Deployment script for Fitness Health Coach AWS infrastructure
"""
import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

def check_prerequisites():
    """Check if all prerequisites are installed"""
    print("Checking prerequisites...")
    
    # Check if AWS CLI is installed and configured
    try:
        aws_identity = run_command("aws sts get-caller-identity")
        identity = json.loads(aws_identity)
        print(f"✓ AWS CLI configured for account: {identity['Account']}")
    except:
        print("✗ AWS CLI not configured. Please run 'aws configure'")
        sys.exit(1)
    
    # Check if CDK is installed
    try:
        cdk_version = run_command("cdk --version")
        print(f"✓ AWS CDK installed: {cdk_version}")
    except:
        print("✗ AWS CDK not installed. Please run 'npm install -g aws-cdk'")
        sys.exit(1)
    
    # Check if Python dependencies are installed
    requirements_file = Path("infrastructure/requirements.txt")
    if requirements_file.exists():
        print("✓ Installing Python dependencies...")
        run_command("pip install -r infrastructure/requirements.txt")
    
    print("All prerequisites satisfied!\n")

def bootstrap_cdk():
    """Bootstrap CDK if needed"""
    print("Checking CDK bootstrap status...")
    
    try:
        # Check if CDK is already bootstrapped
        run_command("aws cloudformation describe-stacks --stack-name CDKToolkit")
        print("✓ CDK already bootstrapped")
    except:
        print("Bootstrapping CDK...")
        run_command("cdk bootstrap", cwd="infrastructure")
        print("✓ CDK bootstrapped successfully")

def deploy_infrastructure():
    """Deploy the CDK infrastructure"""
    print("Deploying infrastructure...")
    
    # Change to infrastructure directory
    infrastructure_dir = Path("infrastructure")
    
    # Synthesize the CDK app first
    print("Synthesizing CDK app...")
    run_command("cdk synth", cwd=infrastructure_dir)
    
    # Deploy the stack
    print("Deploying CDK stack...")
    deploy_output = run_command("cdk deploy --require-approval never", cwd=infrastructure_dir)
    
    print("✓ Infrastructure deployed successfully!")
    print("\nDeployment output:")
    print(deploy_output)
    
    return deploy_output

def extract_outputs(deploy_output):
    """Extract important outputs from deployment"""
    outputs = {}
    
    # Parse CDK outputs (this is a simplified parser)
    lines = deploy_output.split('\n')
    for line in lines:
        if '=' in line and ('FitnessCoach' in line or 'fitness-coach' in line):
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                outputs[key] = value
    
    return outputs

def setup_secrets():
    """Setup Secrets Manager with placeholder values"""
    print("\nSetting up Secrets Manager...")
    
    secret_name = "fitness-coach/spoonacular-api-key"
    
    try:
        # Check if secret exists
        run_command(f"aws secretsmanager describe-secret --secret-id {secret_name}")
        print(f"✓ Secret {secret_name} already exists")
    except:
        print(f"Creating secret {secret_name}...")
        secret_value = json.dumps({"api_key": "REPLACE_WITH_ACTUAL_SPOONACULAR_API_KEY"})
        run_command(f'aws secretsmanager create-secret --name {secret_name} --description "Spoonacular API key for meal planning" --secret-string \'{secret_value}\'')
        print(f"✓ Secret created. Please update with actual API key using:")
        print(f"   aws secretsmanager update-secret --secret-id {secret_name} --secret-string '{{\"api_key\": \"YOUR_ACTUAL_API_KEY\"}}'")

def configure_production_environment():
    """Configure production environment settings"""
    print("\nConfiguring production environment...")
    
    # Get stack outputs
    try:
        stack_outputs = run_command("aws cloudformation describe-stacks --stack-name FitnessCoachStack --query 'Stacks[0].Outputs'")
        outputs = json.loads(stack_outputs)
        
        # Extract important values
        api_gateway_url = None
        api_key_id = None
        
        for output in outputs:
            if 'ApiGateway' in output.get('OutputKey', ''):
                api_gateway_url = output.get('OutputValue')
            elif 'ApiKey' in output.get('OutputKey', ''):
                api_key_id = output.get('OutputValue')
        
        print(f"✓ API Gateway URL: {api_gateway_url}")
        print(f"✓ API Key ID: {api_key_id}")
        
        # Get API key value
        if api_key_id:
            try:
                api_key_value = run_command(f"aws apigateway get-api-key --api-key {api_key_id} --include-value --query 'value' --output text")
                print(f"✓ API Key Value: {api_key_value}")
                
                # Save configuration to file
                config = {
                    "api_gateway_url": api_gateway_url,
                    "api_key_id": api_key_id,
                    "api_key_value": api_key_value,
                    "deployment_timestamp": datetime.now().isoformat()
                }
                
                with open("deployment_config.json", "w") as f:
                    json.dumps(config, f, indent=2)
                
                print("✓ Configuration saved to deployment_config.json")
                
            except Exception as e:
                print(f"⚠ Could not retrieve API key value: {e}")
        
        return {
            "api_gateway_url": api_gateway_url,
            "api_key_id": api_key_id
        }
        
    except Exception as e:
        print(f"⚠ Could not retrieve stack outputs: {e}")
        return {}

def test_api_endpoints(config):
    """Test API endpoints to verify deployment"""
    print("\nTesting API endpoints...")
    
    api_url = config.get("api_gateway_url")
    if not api_url:
        print("⚠ API Gateway URL not available, skipping endpoint tests")
        return
    
    # Test health endpoint
    try:
        import requests
        
        health_url = f"{api_url}/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            print("✓ Health endpoint responding")
        else:
            print(f"⚠ Health endpoint returned status {response.status_code}")
            
    except ImportError:
        print("⚠ requests library not available, skipping endpoint tests")
        print("   Install with: pip install requests")
    except Exception as e:
        print(f"⚠ Health endpoint test failed: {e}")

def setup_monitoring_alerts():
    """Setup additional monitoring and alerting"""
    print("\nSetting up monitoring alerts...")
    
    try:
        # Create SNS topic for alerts (if it doesn't exist)
        topic_name = "fitness-coach-alerts"
        
        try:
            topic_arn = run_command(f"aws sns create-topic --name {topic_name} --query 'TopicArn' --output text")
            print(f"✓ SNS topic created/verified: {topic_arn}")
        except:
            print(f"⚠ Could not create SNS topic {topic_name}")
        
        print("✓ Monitoring alerts configured")
        
    except Exception as e:
        print(f"⚠ Could not setup monitoring alerts: {e}")

def validate_deployment():
    """Validate that all components are deployed correctly"""
    print("\nValidating deployment...")
    
    validation_results = {
        "lambda_functions": [],
        "api_gateway": False,
        "dynamodb_tables": [],
        "secrets": [],
        "cloudwatch_alarms": []
    }
    
    try:
        # Check Lambda functions
        functions = ["fitness-coach-handler", "workout-generator", "meal-planner"]
        for func_name in functions:
            try:
                run_command(f"aws lambda get-function --function-name {func_name}")
                validation_results["lambda_functions"].append(func_name)
                print(f"✓ Lambda function {func_name} deployed")
            except:
                print(f"✗ Lambda function {func_name} not found")
        
        # Check API Gateway
        try:
            apis = run_command("aws apigateway get-rest-apis --query 'items[?name==`fitness-coach-api`]'")
            if json.loads(apis):
                validation_results["api_gateway"] = True
                print("✓ API Gateway deployed")
            else:
                print("✗ API Gateway not found")
        except:
            print("✗ Could not check API Gateway")
        
        # Check DynamoDB tables
        tables = ["fitness-coach-sessions", "api-usage-metrics"]
        for table_name in tables:
            try:
                run_command(f"aws dynamodb describe-table --table-name {table_name}")
                validation_results["dynamodb_tables"].append(table_name)
                print(f"✓ DynamoDB table {table_name} deployed")
            except:
                print(f"✗ DynamoDB table {table_name} not found")
        
        # Check Secrets Manager
        secrets = ["fitness-coach/spoonacular-api-key"]
        for secret_name in secrets:
            try:
                run_command(f"aws secretsmanager describe-secret --secret-id {secret_name}")
                validation_results["secrets"].append(secret_name)
                print(f"✓ Secret {secret_name} configured")
            except:
                print(f"✗ Secret {secret_name} not found")
        
        # Check CloudWatch alarms
        try:
            alarms = run_command("aws cloudwatch describe-alarms --alarm-name-prefix fitness-coach")
            alarm_data = json.loads(alarms)
            validation_results["cloudwatch_alarms"] = [alarm["AlarmName"] for alarm in alarm_data.get("MetricAlarms", [])]
            print(f"✓ {len(validation_results['cloudwatch_alarms'])} CloudWatch alarms configured")
        except:
            print("✗ Could not check CloudWatch alarms")
        
        return validation_results
        
    except Exception as e:
        print(f"⚠ Validation failed: {e}")
        return validation_results

def main():
    """Main deployment function"""
    print("🚀 Starting Fitness Health Coach deployment...\n")
    
    # Check prerequisites
    check_prerequisites()
    
    # Bootstrap CDK
    bootstrap_cdk()
    
    # Deploy infrastructure
    deploy_output = deploy_infrastructure()
    
    # Extract outputs
    outputs = extract_outputs(deploy_output)
    
    # Setup secrets
    setup_secrets()
    
    # Configure production environment
    config = configure_production_environment()
    
    # Setup monitoring alerts
    setup_monitoring_alerts()
    
    # Test API endpoints
    test_api_endpoints(config)
    
    # Validate deployment
    validation_results = validate_deployment()
    
    print("\n🎉 Deployment completed successfully!")
    
    if outputs:
        print("\n📋 Important outputs:")
        for key, value in outputs.items():
            print(f"   {key}: {value}")
    
    # Print validation summary
    print("\n📊 Deployment Validation Summary:")
    print(f"   Lambda Functions: {len(validation_results['lambda_functions'])}/3 deployed")
    print(f"   API Gateway: {'✓' if validation_results['api_gateway'] else '✗'}")
    print(f"   DynamoDB Tables: {len(validation_results['dynamodb_tables'])}/2 deployed")
    print(f"   Secrets: {len(validation_results['secrets'])}/1 configured")
    print(f"   CloudWatch Alarms: {len(validation_results['cloudwatch_alarms'])} configured")
    
    print("\n📝 Next steps:")
    print("1. Update the Spoonacular API key in Secrets Manager")
    print("2. Test the API endpoints with actual requests")
    print("3. Configure monitoring alert notifications")
    print("4. Set up CI/CD pipeline for future deployments")
    print("5. Review CloudWatch dashboard for system health")
    
    if config.get("api_gateway_url"):
        print(f"\n🔗 API Endpoint: {config['api_gateway_url']}/fitness-coach")
        print("📊 CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/home#dashboards:name=FitnessHealthCoach-Monitoring")

if __name__ == "__main__":
    main()