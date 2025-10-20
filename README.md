# 🎯 AI Fitness Health Coach - Complete System

AWS-powered serverless fitness and nutrition coaching system with **MCP (Model Context Protocol)** integration. Features AI-powered workout generation, intelligent meal planning, and real-time AWS documentation access.

[![AWS](https://img.shields.io/badge/AWS-Serverless-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org/)
[![MCP](https://img.shields.io/badge/MCP-Integration-green)](https://modelcontextprotocol.io/)

## 🌟 **Key Features**

- 🏋️ **AI Workout Generation** - Personalized workouts with Bedrock AI + Fitness Knowledge MCP
- 🍽️ **Smart Meal Planning** - USDA nutrition database + intelligent caching  
- 📚 **Real-time AWS Docs** - Instant access to AWS documentation during development
- ☁️ **Serverless Architecture** - Lambda, DynamoDB, API Gateway, S3
- 🔧 **MCP Integration** - Enhanced AI with specialized knowledge servers
- 🚀 **Production Ready** - Comprehensive monitoring, testing, and deployment

## 🎮 **Quick Start (No API Keys Needed!)**

```bash
# 1. Clone the repository
git clone https://github.com/amruthavinayakam/AI_FitnessHealthCoach.git
cd AI_FitnessHealthCoach

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start local development server
py local_server.py

# 4. Visit http://localhost:8080
# Try: "I want to build muscle and lose fat"
```

## 📊 **System Architecture**

```
User Request → API Gateway → Lambda Functions → {
    ├── Workout Generator + Fitness Knowledge MCP
    └── Meal Planner + Enhanced Nutrition MCP  
} → Bedrock AI → Enhanced Response
```

### 🔧 **MCP Servers**

1. **Fitness Knowledge MCP** - Exercise database with form descriptions and safety guidelines
2. **Enhanced Nutrition MCP** - USDA nutrition data with intelligent meal planning
3. **AWS Documentation MCP** - Real-time AWS documentation access

## 📁 **Project Structure**

```
AI_FitnessHealthCoach/
├── src/
│   ├── lambda/                          # AWS Lambda functions
│   │   ├── fitness_coach_handler/       # Main API handler
│   │   ├── workout_generator/           # AI workout generation
│   │   └── meal_planner/               # Nutrition planning
│   ├── mcp_servers/                    # MCP server implementations
│   │   ├── fitness_knowledge/          # Exercise database & expertise
│   │   ├── nutrition_enhanced/         # USDA nutrition database
│   │   └── spoonacular_enhanced/       # Spoonacular API integration
│   └── shared/                         # Shared utilities
├── infrastructure/                     # AWS CDK infrastructure
├── tests/                             # Comprehensive test suite
├── docs/                              # Documentation
└── .kiro/specs/                       # Feature specifications
```

## 🚀 **Deployment Options**

### **Option 1: Local Development (Recommended for testing)**
```bash
py local_server.py
# Visit http://localhost:8080
```

### **Option 2: AWS Deployment**
```bash
# Configure AWS credentials
aws configure

# Deploy infrastructure
py deploy.py

# Your API will be available at the provided endpoint
```

## 🔒 **Environment Setup**

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure optional API keys in `.env`:**
   ```bash
   # Optional - system works without these
   SPOONACULAR_API_KEY=your-key-here
   USDA_API_KEY=your-key-here
   
   # Required for AWS deployment
   AWS_REGION=us-east-1
   AWS_ACCOUNT_ID=123456789012
   ```

3. **The system works perfectly without any API keys using:**
   - Enhanced Nutrition Database (USDA data)
   - Fitness Knowledge MCP Server
   - Demo mode for testing

## 🍽️ **Nutrition Data Sources**

### **Enhanced Nutrition Database (Default)**
- ✅ **FREE** - No API keys required
- ✅ **USDA FoodData Central** - Official government nutrition data
- ✅ **30+ Foods** - Comprehensive database
- ✅ **6+ Recipes** - Quality meal templates
- ✅ **Instant Response** - No external dependencies

### **Optional API Integrations**
- **USDA FoodData Central API** - 1,000 requests/hour (free)
- **Edamam Recipe API** - 10,000 requests/month (free tier)
- **Open Food Facts API** - Unlimited (open source)

## 🏋️ **Fitness Knowledge**

The Fitness Knowledge MCP Server includes:
- **Exercise Database** - 5+ exercises with detailed information
- **Form Descriptions** - Proper exercise technique
- **Safety Guidelines** - Injury prevention tips
- **Progressive Overload** - Workout advancement recommendations
- **Balance Validation** - Ensure balanced muscle group targeting

## 🧪 **Testing**

```bash
# Run all tests
py tests/run_tests.py

# Test MCP servers
py src/mcp_servers/fitness_knowledge/server.py
py src/mcp_servers/nutrition_enhanced/multi_source_server.py

# Test API integration
py test_real_vs_demo.py
```

## 🔧 **Configuration**

```bash
# Configure nutrition data source
py configure_apis.py

# Options:
# 1. Enhanced Nutrition Database (USDA + Custom)
# 2. Demo mode (simple sample data)  
# 3. Spoonacular API (requires API key)
```

## 📊 **Monitoring & Observability**

- **CloudWatch Dashboards** - Real-time metrics
- **API Gateway Monitoring** - Request/response tracking
- **Lambda Performance** - Execution time and errors
- **DynamoDB Metrics** - Read/write capacity and throttling
- **Custom Alarms** - Proactive issue detection

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **AWS Bedrock** - AI model integration
- **USDA FoodData Central** - Nutrition database
- **Model Context Protocol** - Enhanced AI capabilities
- **AWS CDK** - Infrastructure as code
- **Kiro IDE** - Development environment

---

**🎯 Built with ❤️ for the fitness and health community**