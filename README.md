# Fitness Health Coach System

AWS-powered serverless chatbot system that provides personalized fitness and nutrition guidance using AWS Bedrock and Spoonacular API.

## Project Structure

```
├── src/
│   ├── lambda/
│   │   ├── fitness_coach_handler/    # Main API handler
│   │   ├── workout_generator/        # Bedrock integration for workouts
│   │   └── meal_planner/            # Spoonacular integration for meals
│   └── mcp_servers/
│       ├── fitness_knowledge/       # Custom fitness MCP server
│       └── spoonacular_enhanced/    # Enhanced Spoonacular MCP server
├── infrastructure/
│   ├── app.py                       # CDK app entry point
│   ├── fitness_coach_stack.py       # Main CDK stack
│   └── requirements.txt             # CDK dependencies
├── .kiro/settings/mcp.json          # MCP server configuration
├── cdk.json                         # CDK configuration
├── deploy.py                        # Deployment script
└── requirements.txt                 # Project dependencies
```

## AWS Services Used

- **AWS Bedrock**: AI-powered workout plan generation (Claude 3 Haiku)
- **AWS Lambda**: Serverless compute functions
- **Amazon API Gateway**: REST API endpoints
- **Amazon DynamoDB**: User sessions and metrics storage
- **Amazon S3**: Static assets and temporary files
- **AWS Secrets Manager**: Secure API key storage
- **Amazon CloudWatch**: Logging and monitoring

## Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate permissions
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Spoonacular API key

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Deploy infrastructure:**
   ```bash
   python deploy.py
   ```

3. **Configure Spoonacular API key:**
   - Go to AWS Secrets Manager console
   - Find secret: `fitness-coach/spoonacular-api-key`
   - Update the `api_key` value with your Spoonacular API key

4. **Test the API:**
   ```bash
   # Get API Gateway URL from CDK output
   curl -X POST https://your-api-id.execute-api.region.amazonaws.com/prod/fitness-coach \
     -H "Content-Type: application/json" \
     -d '{"username": "test", "userId": "123", "query": "I want to build muscle"}'
   ```

## MCP Server Integration

The system uses MCP servers for enhanced functionality:

- **AWS Documentation MCP Server**: Real-time AWS documentation access
- **Custom Fitness Knowledge MCP Server**: Exercise database and expertise
- **Custom Spoonacular MCP Server**: Enhanced meal planning with caching

## Development

1. **Local testing:**
   ```bash
   # Test individual Lambda functions
   cd src/lambda/fitness_coach_handler
   python handler.py
   ```

2. **CDK commands:**
   ```bash
   cdk synth    # Synthesize CloudFormation template
   cdk diff     # Show differences
   cdk deploy   # Deploy stack
   cdk destroy  # Clean up resources
   ```

## Requirements Mapping

This implementation addresses the following requirements:
- **6.1**: AWS Bedrock integration for LLM operations
- **6.2**: AWS Lambda for serverless compute
- **6.3**: Amazon DynamoDB for data storage
- **6.4**: AWS Secrets Manager for API keys
- **6.5**: Amazon S3 for file storage
- **6.6**: Amazon CloudWatch for monitoring

## Next Steps

1. Implement core data models and validation (Task 2)
2. Develop MCP servers for enhanced functionality (Task 3)
3. Integrate AWS Bedrock for workout generation (Task 4)
4. Implement Spoonacular API integration (Task 5)
5. Create main Lambda function handler (Task 6)