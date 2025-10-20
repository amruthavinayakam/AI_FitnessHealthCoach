# MCP Server Integration Guide

## Overview

This document describes how to use the Model Context Protocol (MCP) servers integrated into the Fitness Health Coach development environment. MCP servers provide enhanced capabilities for accessing AWS documentation, fitness knowledge, and Spoonacular API optimization.

## Configured MCP Servers

### 1. AWS Documentation MCP Server

**Purpose**: Real-time access to AWS service documentation and best practices during development.

**Configuration**: Already configured in `.kiro/settings/mcp.json`

**Available Tools**:
- `search_documentation`: Search AWS documentation for specific topics
- `read_documentation`: Read full AWS documentation pages
- `recommend`: Get recommendations for related AWS documentation

**Usage Examples**:

#### Searching AWS Documentation
```python
# Search for Bedrock model information
search_results = mcp_search("AWS Bedrock Claude models", limit=5)
```

#### Reading Specific Documentation
```python
# Read detailed Bedrock model parameters
doc_content = mcp_read_documentation(
    "https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html"
)
```

#### Getting Recommendations
```python
# Get related documentation for a specific page
recommendations = mcp_recommend(
    "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html"
)
```

### 2. Development Workflow Integration

#### When to Use AWS Documentation MCP Server

1. **Infrastructure Development**:
   - Query DynamoDB best practices and schema design patterns
   - Get Lambda configuration recommendations
   - Access CloudWatch monitoring setup guides
   - Retrieve API Gateway security configurations

2. **Service Integration**:
   - Bedrock model capabilities and pricing information
   - Secrets Manager configuration patterns
   - S3 bucket policies and permissions
   - IAM role and policy examples

3. **Troubleshooting**:
   - Error code explanations and solutions
   - Service limits and quotas
   - Performance optimization guides
   - Security best practices

#### Example Development Scenarios

**Scenario 1: Configuring Bedrock Model Parameters**
```bash
# Search for Claude model parameters
mcp_search("Bedrock Claude model parameters temperature")

# Read detailed configuration guide
mcp_read_documentation("https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html")
```

**Scenario 2: DynamoDB Schema Design**
```bash
# Search for DynamoDB best practices
mcp_search("DynamoDB table design best practices")

# Get recommendations for related topics
mcp_recommend("https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html")
```

**Scenario 3: Lambda Performance Optimization**
```bash
# Search for Lambda performance guidelines
mcp_search("Lambda function performance optimization memory")

# Read detailed performance guide
mcp_read_documentation("https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html")
```

## Testing MCP Server Integration

### Verification Steps

1. **Test AWS Documentation Search**:
   ```python
   # Test search functionality
   results = mcp_search("AWS Bedrock pricing", limit=3)
   assert len(results) > 0
   assert "bedrock" in results[0]["title"].lower()
   ```

2. **Test Documentation Reading**:
   ```python
   # Test reading functionality
   content = mcp_read_documentation(
       "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html",
       max_length=1000
   )
   assert "Amazon Bedrock" in content
   ```

3. **Test Recommendations**:
   ```python
   # Test recommendation functionality
   recommendations = mcp_recommend(
       "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html"
   )
   assert len(recommendations) > 0
   ```

## Best Practices

### 1. Efficient Documentation Queries

- Use specific search terms to get relevant results
- Include service names in searches (e.g., "DynamoDB", "Lambda", "Bedrock")
- Use quotes for exact phrase matching

### 2. Development Workflow

- Query documentation before implementing new AWS service integrations
- Use recommendations to discover related best practices
- Cache frequently accessed documentation locally for offline reference

### 3. Performance Considerations

- Limit search results to avoid overwhelming output
- Use specific URLs when you know the exact documentation page
- Combine multiple queries for comprehensive understanding

## Troubleshooting

### Common Issues

1. **MCP Server Not Responding**:
   - Check if `uv` is installed and accessible
   - Verify network connectivity
   - Check MCP server logs in Kiro

2. **Search Returns No Results**:
   - Try broader search terms
   - Check spelling and service names
   - Use alternative keywords

3. **Documentation Reading Fails**:
   - Verify the URL is from docs.aws.amazon.com
   - Check if the page exists and is accessible
   - Try with a smaller max_length parameter

### Getting Help

- Check MCP server status in Kiro's MCP Server view
- Review server logs for error messages
- Restart MCP servers if needed through Kiro interface

## Future Enhancements

### Planned MCP Servers

1. **Custom Fitness Knowledge MCP Server**: Exercise database and fitness expertise
2. **Custom Spoonacular MCP Server**: Enhanced meal planning with caching and optimization

These servers will be deployed as part of task 9.2 and will provide runtime capabilities for the fitness coach application.