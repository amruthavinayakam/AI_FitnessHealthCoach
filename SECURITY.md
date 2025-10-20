# 🔒 Security Guidelines

## Environment Variables

This project uses environment variables for sensitive configuration. **Never commit actual API keys or secrets to the repository.**

### Setup Instructions:

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in your actual values in `.env`:**
   ```bash
   # Edit .env with your real API keys
   SPOONACULAR_API_KEY=your-actual-key-here
   AWS_ACCOUNT_ID=123456789012
   ```

3. **The `.env` file is automatically ignored by git** - it will never be committed.

## API Keys Required:

### Optional (System works without these):
- **Spoonacular API**: Get from https://spoonacular.com/food-api (free tier: 150 requests/day)
- **USDA API**: Get from https://fdc.nal.usda.gov/api-guide.html (free: 1000 requests/hour)
- **Edamam API**: Get from https://developer.edamam.com/ (free tier: 10,000 requests/month)

### AWS (Required for deployment):
- **AWS Account**: Configure with `aws configure`
- **AWS CDK**: Installed and bootstrapped

## What's Safe to Commit:

✅ **Safe:**
- Code files
- Configuration templates (`.env.example`)
- Documentation
- Test files
- Infrastructure code (CDK)

❌ **Never Commit:**
- `.env` files
- API keys
- AWS credentials
- Personal configuration files
- Deployment artifacts with secrets

## Local Development:

The system is designed to work **without any API keys** using:
- Enhanced Nutrition Database (USDA data)
- Fitness Knowledge MCP Server
- Demo mode for testing

## Production Deployment:

Use AWS Secrets Manager for production secrets:
```bash
aws secretsmanager create-secret --name "fitness-coach/api-keys" --secret-string '{"spoonacular":"your-key"}'
```