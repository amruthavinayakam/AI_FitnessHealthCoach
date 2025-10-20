"""
AWS CDK Stack for Fitness Health Coach System
"""
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from monitoring_dashboard import FitnessCoachMonitoringDashboard

class FitnessCoachStack(Stack):
    """
    Main CDK Stack for Fitness Health Coach System
    Implements requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create DynamoDB tables
        self._create_dynamodb_tables()
        
        # Create S3 bucket
        self._create_s3_bucket()
        
        # Create Secrets Manager for API keys
        self._create_secrets()
        
        # Create Lambda functions
        self._create_lambda_functions()
        
        # Create API Gateway
        self._create_api_gateway()
        
        # Create IAM roles and policies
        self._create_iam_resources()
        
        # Create CloudWatch monitoring and logging
        self._create_monitoring_and_logging()
        
        # Create monitoring dashboard - temporarily disabled for deployment
        # self._create_monitoring_dashboard()
    
    def _create_dynamodb_tables(self):
        """Create DynamoDB tables for sessions and metrics"""
        # Sessions table with TTL
        self.sessions_table = dynamodb.Table(
            self, "FitnessCoachSessions",
            table_name="fitness-coach-sessions",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sessionId", 
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )       
 
        # API usage metrics table
        self.metrics_table = dynamodb.Table(
            self, "ApiUsageMetrics",
            table_name="api-usage-metrics",
            partition_key=dynamodb.Attribute(
                name="date",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
    
    def _create_s3_bucket(self):
        """Create S3 bucket for static assets and temporary files"""
        self.s3_bucket = s3.Bucket(
            self, "FitnessCoachBucket",
            bucket_name=f"fitness-coach-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED
        )
    
    def _create_secrets(self):
        """Create Secrets Manager for nutrition API keys"""
        self.nutrition_secret = secretsmanager.Secret(
            self, "NutritionApiKeys",
            secret_name="fitness-coach/nutrition-api-keys",
            description="Optional API keys for enhanced nutrition features (USDA, Edamam)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"usda_api_key": "", "edamam_app_id": "", "edamam_app_key": ""}',
                generate_string_key="usda_api_key",
                exclude_characters=' "%@/\\'
            )
        )    

    def _create_lambda_functions(self):
        """Create Lambda functions for the fitness coach system"""
        
        # Shared environment variables
        common_env = {
            "LOG_LEVEL": "INFO",
            "POWERTOOLS_SERVICE_NAME": "fitness-coach"
        }
        
        # Main handler Lambda function
        self.main_handler = _lambda.Function(
            self, "FitnessCoachHandler",
            function_name="fitness-coach-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda/fitness_coach_handler"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                **common_env,
                "DYNAMODB_SESSIONS_TABLE": self.sessions_table.table_name,
                "DYNAMODB_METRICS_TABLE": self.metrics_table.table_name,
                "S3_BUCKET_NAME": self.s3_bucket.bucket_name,
                "NUTRITION_SECRET_ARN": self.nutrition_secret.secret_arn,
                "WORKOUT_GENERATOR_FUNCTION": "workout-generator",
                "MEAL_PLANNER_FUNCTION": "meal-planner"
            },
            dead_letter_queue_enabled=True
        )
        
        # Workout generator Lambda function
        self.workout_generator = _lambda.Function(
            self, "WorkoutGenerator",
            function_name="workout-generator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda/workout_generator"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                **common_env,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
                "BEDROCK_REGION": self.region
            },
            dead_letter_queue_enabled=True
        )
        
        # Meal planner Lambda function
        self.meal_planner = _lambda.Function(
            self, "MealPlanner", 
            function_name="meal-planner",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda/meal_planner"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                **common_env,
                "NUTRITION_SECRET_ARN": self.nutrition_secret.secret_arn,
                "NUTRITION_DATABASE": "enhanced"
            },
            dead_letter_queue_enabled=True
        )    

    def _create_api_gateway(self):
        """Create API Gateway for REST API with rate limiting and authentication"""
        self.api = apigateway.RestApi(
            self, "FitnessCoachApi",
            rest_api_name="fitness-coach-api",
            description="Fitness Health Coach API Gateway",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )
        
        # Create API Key for authentication
        self.api_key = apigateway.ApiKey(
            self, "FitnessCoachApiKey",
            api_key_name="fitness-coach-api-key",
            description="API Key for Fitness Coach API"
        )
        
        # Create Usage Plan with rate limiting
        self.usage_plan = apigateway.UsagePlan(
            self, "FitnessCoachUsagePlan",
            name="fitness-coach-usage-plan",
            description="Usage plan for Fitness Coach API with rate limiting",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100,  # 100 requests per second
                burst_limit=200  # 200 burst requests
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,  # 10,000 requests per day
                period=apigateway.Period.DAY
            )
        )
        
        # Associate API key with usage plan
        self.usage_plan.add_api_key(self.api_key)
        
        # Associate API with usage plan
        self.usage_plan.add_api_stage(
            stage=self.api.deployment_stage
        )
        
        # Create request validator
        request_validator = apigateway.RequestValidator(
            self, "FitnessCoachRequestValidator",
            rest_api=self.api,
            validate_request_body=True,
            validate_request_parameters=True
        )
        
        # Create request model for validation
        request_model = apigateway.Model(
            self, "FitnessCoachRequestModel",
            rest_api=self.api,
            content_type="application/json",
            model_name="FitnessCoachRequest",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "username": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        min_length=1,
                        max_length=50
                    ),
                    "userId": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        min_length=1,
                        max_length=100
                    ),
                    "query": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        min_length=1,
                        max_length=1000
                    )
                },
                required=["username", "userId", "query"]
            )
        )
        
        # Create /fitness-coach endpoint
        fitness_coach_resource = self.api.root.add_resource("fitness-coach")
        
        # Add POST method with Lambda integration
        fitness_coach_integration = apigateway.LambdaIntegration(
            self.main_handler,
            request_templates={"application/json": '{"statusCode": "200"}'},
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_templates={
                        "application/json": ""
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="400",
                    selection_pattern=".*Bad Request.*",
                    response_templates={
                        "application/json": '{"error": "Bad Request"}'
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="500", 
                    selection_pattern=".*Internal Server Error.*",
                    response_templates={
                        "application/json": '{"error": "Internal Server Error"}'
                    }
                )
            ]
        )
        
        fitness_coach_resource.add_method(
            "POST",
            fitness_coach_integration,
            api_key_required=True,  # Require API key for production
            request_validator=request_validator,
            request_models={
                "application/json": request_model
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL
                    }
                ),
                apigateway.MethodResponse(
                    status_code="400",
                    response_models={
                        "application/json": apigateway.Model.ERROR_MODEL
                    }
                ),
                apigateway.MethodResponse(
                    status_code="500",
                    response_models={
                        "application/json": apigateway.Model.ERROR_MODEL
                    }
                )
            ]
        )
    
    def _create_iam_resources(self):
        """Create IAM roles and policies with least privilege access"""
        
        # Grant DynamoDB permissions to main handler
        self.sessions_table.grant_read_write_data(self.main_handler)
        self.metrics_table.grant_read_write_data(self.main_handler)
        
        # Grant S3 permissions
        self.s3_bucket.grant_read_write(self.main_handler)
        
        # Grant Secrets Manager permissions
        self.nutrition_secret.grant_read(self.main_handler)
        self.nutrition_secret.grant_read(self.meal_planner)
        
        # Grant Lambda invocation permissions to main handler
        lambda_invoke_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "lambda:InvokeFunction"
            ],
            resources=[
                self.workout_generator.function_arn,
                self.meal_planner.function_arn
            ]
        )
        self.main_handler.add_to_role_policy(lambda_invoke_policy)
        
        # Grant Bedrock permissions to workout generator
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
            ]
        )
        self.workout_generator.add_to_role_policy(bedrock_policy)
        
        # Grant CloudWatch Logs permissions (enhanced)
        cloudwatch_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream", 
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
                "logs:DescribeLogGroups"
            ],
            resources=[
                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/*"
            ]
        )
        
        # Add CloudWatch permissions to all Lambda functions
        for lambda_function in [self.main_handler, self.workout_generator, self.meal_planner]:
            lambda_function.add_to_role_policy(cloudwatch_policy)
        
        # Grant CloudWatch Logs permissions (automatically handled by CDK)
        # All Lambda functions get CloudWatch Logs permissions by default
    
    def _create_monitoring_and_logging(self):
        """Create CloudWatch monitoring, logging, and alarms"""
        
        # Create CloudWatch Log Groups with retention
        self.main_handler_log_group = logs.LogGroup(
            self, "MainHandlerLogGroup",
            log_group_name=f"/aws/lambda/{self.main_handler.function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        self.workout_generator_log_group = logs.LogGroup(
            self, "WorkoutGeneratorLogGroup", 
            log_group_name=f"/aws/lambda/{self.workout_generator.function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        self.meal_planner_log_group = logs.LogGroup(
            self, "MealPlannerLogGroup",
            log_group_name=f"/aws/lambda/{self.meal_planner.function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create CloudWatch Alarms for Lambda error rates
        self._create_lambda_alarms()
        
        # Create CloudWatch Alarms for API Gateway
        self._create_api_gateway_alarms()
        
        # Create CloudWatch Alarms for DynamoDB
        self._create_dynamodb_alarms()
    
    def _create_lambda_alarms(self):
        """Create CloudWatch alarms for Lambda functions"""
        
        # Main handler error rate alarm
        cloudwatch.Alarm(
            self, "MainHandlerErrorAlarm",
            alarm_name="fitness-coach-main-handler-errors",
            alarm_description="Main handler Lambda error rate > 5%",
            metric=self.main_handler.metric_errors(
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Main handler duration alarm
        cloudwatch.Alarm(
            self, "MainHandlerDurationAlarm", 
            alarm_name="fitness-coach-main-handler-duration",
            alarm_description="Main handler Lambda duration > 25 seconds",
            metric=self.main_handler.metric_duration(
                period=Duration.minutes(5)
            ),
            threshold=25000,  # 25 seconds in milliseconds
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Workout generator error rate alarm
        cloudwatch.Alarm(
            self, "WorkoutGeneratorErrorAlarm",
            alarm_name="fitness-coach-workout-generator-errors", 
            alarm_description="Workout generator Lambda error rate > 5%",
            metric=self.workout_generator.metric_errors(
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Meal planner error rate alarm
        cloudwatch.Alarm(
            self, "MealPlannerErrorAlarm",
            alarm_name="fitness-coach-meal-planner-errors",
            alarm_description="Meal planner Lambda error rate > 5%", 
            metric=self.meal_planner.metric_errors(
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
    
    def _create_api_gateway_alarms(self):
        """Create CloudWatch alarms for API Gateway"""
        
        # API Gateway 4xx error rate alarm
        cloudwatch.Alarm(
            self, "ApiGateway4xxAlarm",
            alarm_name="fitness-coach-api-4xx-errors",
            alarm_description="API Gateway 4xx error rate > 10%",
            metric=self.api.metric_client_error(
                period=Duration.minutes(5)
            ),
            threshold=10,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # API Gateway 5xx error rate alarm  
        cloudwatch.Alarm(
            self, "ApiGateway5xxAlarm",
            alarm_name="fitness-coach-api-5xx-errors",
            alarm_description="API Gateway 5xx error rate > 5%",
            metric=self.api.metric_server_error(
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # API Gateway latency alarm
        cloudwatch.Alarm(
            self, "ApiGatewayLatencyAlarm",
            alarm_name="fitness-coach-api-latency",
            alarm_description="API Gateway latency > 10 seconds",
            metric=self.api.metric_latency(
                period=Duration.minutes(5)
            ),
            threshold=10000,  # 10 seconds in milliseconds
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
    
    def _create_dynamodb_alarms(self):
        """Create CloudWatch alarms for DynamoDB tables"""
        
        # Sessions table throttled requests alarm
        cloudwatch.Alarm(
            self, "SessionsTableThrottleAlarm",
            alarm_name="fitness-coach-sessions-throttled",
            alarm_description="Sessions table throttled requests > 0",
            metric=self.sessions_table.metric_throttled_requests(
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Metrics table throttled requests alarm
        cloudwatch.Alarm(
            self, "MetricsTableThrottleAlarm", 
            alarm_name="fitness-coach-metrics-throttled",
            alarm_description="Metrics table throttled requests > 0",
            metric=self.metrics_table.metric_throttled_requests(
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
    
    def _create_monitoring_dashboard(self):
        """Create comprehensive monitoring dashboard"""
        
        # Prepare lambda functions dict
        lambda_functions = {
            'main_handler': self.main_handler,
            'workout_generator': self.workout_generator,
            'meal_planner': self.meal_planner
        }
        
        # Prepare DynamoDB tables dict
        dynamodb_tables = {
            'sessions': self.sessions_table,
            'metrics': self.metrics_table
        }
        
        # Create monitoring dashboard
        self.monitoring_dashboard = FitnessCoachMonitoringDashboard(
            self, "MonitoringDashboard",
            api_gateway=self.api,
            lambda_functions=lambda_functions,
            dynamodb_tables=dynamodb_tables
        )
        
        # Create operational alarms
        self.monitoring_dashboard.create_operational_alarms()