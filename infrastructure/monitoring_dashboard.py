"""
CloudWatch Dashboard configuration for Fitness Health Coach monitoring
Implements requirements 6.6, 4.1, 4.2 for comprehensive monitoring
"""
from aws_cdk import (
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    Duration
)
from constructs import Construct
from typing import List

class FitnessCoachMonitoringDashboard(Construct):
    """
    CloudWatch Dashboard for comprehensive monitoring of Fitness Health Coach system
    """
    
    def __init__(self, scope: Construct, construct_id: str, 
                 api_gateway, lambda_functions: dict, dynamodb_tables: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        self.api_gateway = api_gateway
        self.lambda_functions = lambda_functions
        self.dynamodb_tables = dynamodb_tables
        
        # Create the main dashboard
        self.dashboard = self._create_dashboard()
        
        # Create custom metrics
        self._create_custom_metrics()
    
    def _create_dashboard(self) -> cloudwatch.Dashboard:
        """Create the main CloudWatch dashboard"""
        dashboard = cloudwatch.Dashboard(
            self, "FitnessCoachDashboard",
            dashboard_name="FitnessHealthCoach-Monitoring",
            period_override=cloudwatch.PeriodOverride.AUTO
        )
        
        # Add widgets to dashboard
        dashboard.add_widgets(
            # API Gateway metrics row
            self._create_api_gateway_widgets(),
            
            # Lambda functions metrics row
            self._create_lambda_widgets(),
            
            # DynamoDB metrics row
            self._create_dynamodb_widgets(),
            
            # Business metrics row
            self._create_business_metrics_widgets(),
            
            # Error tracking row
            self._create_error_tracking_widgets()
        )
        
        return dashboard
    
    def _create_api_gateway_widgets(self) -> List[cloudwatch.IWidget]:
        """Create API Gateway monitoring widgets"""
        return [
            # API Gateway Request Count
            cloudwatch.GraphWidget(
                title="API Gateway - Request Count",
                left=[
                    self.api_gateway.metric_count(
                        period=Duration.minutes(5)
                    )
                ],
                width=8,
                height=6
            ),
            
            # API Gateway Latency
            cloudwatch.GraphWidget(
                title="API Gateway - Latency",
                left=[
                    self.api_gateway.metric_latency(
                        period=Duration.minutes(5)
                    )
                ],
                width=8,
                height=6
            ),
            
            # API Gateway Error Rates
            cloudwatch.GraphWidget(
                title="API Gateway - Error Rates",
                left=[
                    self.api_gateway.metric_client_error(
                        period=Duration.minutes(5)
                    ),
                    self.api_gateway.metric_server_error(
                        period=Duration.minutes(5)
                    )
                ],
                width=8,
                height=6
            )
        ]
    
    def _create_lambda_widgets(self) -> List[cloudwatch.IWidget]:
        """Create Lambda functions monitoring widgets"""
        widgets = []
        
        # Lambda Duration
        widgets.append(
            cloudwatch.GraphWidget(
                title="Lambda Functions - Duration",
                left=[
                    func.metric_duration(period=Duration.minutes(5))
                    for func in self.lambda_functions.values()
                ],
                width=12,
                height=6
            )
        )
        
        # Lambda Error Count
        widgets.append(
            cloudwatch.GraphWidget(
                title="Lambda Functions - Errors",
                left=[
                    func.metric_errors(period=Duration.minutes(5))
                    for func in self.lambda_functions.values()
                ],
                width=12,
                height=6
            )
        )
        
        # Lambda Invocations
        widgets.append(
            cloudwatch.GraphWidget(
                title="Lambda Functions - Invocations",
                left=[
                    func.metric_invocations(period=Duration.minutes(5))
                    for func in self.lambda_functions.values()
                ],
                width=12,
                height=6
            )
        )
        
        # Lambda Throttles
        widgets.append(
            cloudwatch.GraphWidget(
                title="Lambda Functions - Throttles",
                left=[
                    func.metric_throttles(period=Duration.minutes(5))
                    for func in self.lambda_functions.values()
                ],
                width=12,
                height=6
            )
        )
        
        return widgets
    
    def _create_dynamodb_widgets(self) -> List[cloudwatch.IWidget]:
        """Create DynamoDB monitoring widgets"""
        widgets = []
        
        # DynamoDB Read/Write Capacity
        widgets.append(
            cloudwatch.GraphWidget(
                title="DynamoDB - Consumed Capacity",
                left=[
                    table.metric_consumed_read_capacity_units(
                        period=Duration.minutes(5)
                    )
                    for table in self.dynamodb_tables.values()
                ],
                right=[
                    table.metric_consumed_write_capacity_units(
                        period=Duration.minutes(5)
                    )
                    for table in self.dynamodb_tables.values()
                ],
                width=12,
                height=6
            )
        )
        
        # DynamoDB Throttled Requests
        widgets.append(
            cloudwatch.GraphWidget(
                title="DynamoDB - Throttled Requests",
                left=[
                    table.metric_throttled_requests(
                        period=Duration.minutes(5)
                    )
                    for table in self.dynamodb_tables.values()
                ],
                width=12,
                height=6
            )
        )
        
        return widgets
    
    def _create_business_metrics_widgets(self) -> List[cloudwatch.IWidget]:
        """Create business metrics widgets"""
        return [
            # Workout Plan Generation Success Rate
            cloudwatch.SingleValueWidget(
                title="Workout Plan Success Rate",
                metrics=[
                    cloudwatch.Metric(
                        namespace="FitnessCoach/Business",
                        metric_name="WorkoutPlanSuccess",
                        statistic="Average",
                        period=Duration.hours(1)
                    )
                ],
                width=6,
                height=6
            ),
            
            # Meal Plan Generation Success Rate
            cloudwatch.SingleValueWidget(
                title="Meal Plan Success Rate",
                metrics=[
                    cloudwatch.Metric(
                        namespace="FitnessCoach/Business",
                        metric_name="MealPlanSuccess",
                        statistic="Average",
                        period=Duration.hours(1)
                    )
                ],
                width=6,
                height=6
            ),
            
            # User Requests per Hour
            cloudwatch.GraphWidget(
                title="User Requests per Hour",
                left=[
                    cloudwatch.Metric(
                        namespace="FitnessCoach/Business",
                        metric_name="UserRequests",
                        statistic="Sum",
                        period=Duration.hours(1)
                    )
                ],
                width=12,
                height=6
            )
        ]
    
    def _create_error_tracking_widgets(self) -> List[cloudwatch.IWidget]:
        """Create error tracking widgets"""
        # Temporarily disabled due to CDK version compatibility issues
        return [
            # Log Insights - Error Analysis
            # Temporarily disabled due to CDK version compatibility
            # cloudwatch.LogQueryWidget(
            #     title="Recent Errors",
            #     log_groups=[
            #         logs.LogGroup.from_log_group_name(
            #             self, f"LogGroup{name}",
            #             log_group_name=f"/aws/lambda/{func.function_name}"
            #         )
            #         for name, func in self.lambda_functions.items()
            #     ],
            #     query_lines=[
            #         "fields @timestamp, @message, level, service, correlation_id",
            #         "filter level = \"ERROR\"",
            #         "sort @timestamp desc",
            #         "limit 100"
            #     ],
            #     width=24,
            #     height=8
            # ),
            
            # Performance Metrics - Temporarily disabled
            # cloudwatch.LogQueryWidget(
            #     title="Performance Metrics",
            #     log_groups=[
            #         logs.LogGroup.from_log_group_name(
            #             self, f"PerfLogGroup{name}",
            #             log_group_name=f"/aws/lambda/{func.function_name}"
            #         )
            #         for name, func in self.lambda_functions.items()
            #     ],
            #     query_lines=[
            #         "fields @timestamp, event_type, execution_time_seconds, service",
            #         "filter event_type = \"performance_metric\"",
            #         "stats avg(execution_time_seconds) by service",
            #         "sort @timestamp desc"
            #     ],
            #     width=24,
            #     height=8
            # )
        ]
    
    def _create_custom_metrics(self):
        """Create custom CloudWatch metrics for business events"""
        
        # Create metric filters for business events
        for name, func in self.lambda_functions.items():
            log_group = logs.LogGroup.from_log_group_name(
                self, f"CustomMetricLogGroup{name}",
                log_group_name=f"/aws/lambda/{func.function_name}"
            )
            
            # Workout plan success metric
            logs.MetricFilter(
                self, f"WorkoutPlanSuccessMetric{name}",
                log_group=log_group,
                metric_namespace="FitnessCoach/Business",
                metric_name="WorkoutPlanSuccess",
                filter_pattern=logs.FilterPattern.literal(
                    '[timestamp, level="INFO", service, message="Workout plan generated successfully*"]'
                ),
                metric_value="1"
            )
            
            # Meal plan success metric
            logs.MetricFilter(
                self, f"MealPlanSuccessMetric{name}",
                log_group=log_group,
                metric_namespace="FitnessCoach/Business",
                metric_name="MealPlanSuccess",
                filter_pattern=logs.FilterPattern.literal(
                    '[timestamp, level="INFO", service, message="Meal plan generated successfully*"]'
                ),
                metric_value="1"
            )
            
            # User request metric
            logs.MetricFilter(
                self, f"UserRequestMetric{name}",
                log_group=log_group,
                metric_namespace="FitnessCoach/Business",
                metric_name="UserRequests",
                filter_pattern=logs.FilterPattern.literal(
                    '[timestamp, level="INFO", service, message="Processing fitness coach request*"]'
                ),
                metric_value="1"
            )
            
            # Error rate metric
            logs.MetricFilter(
                self, f"ErrorRateMetric{name}",
                log_group=log_group,
                metric_namespace="FitnessCoach/Errors",
                metric_name="ErrorCount",
                filter_pattern=logs.FilterPattern.literal(
                    '[timestamp, level="ERROR", ...]'
                ),
                metric_value="1"
            )
    
    def create_operational_alarms(self):
        """Create operational alarms for the system"""
        
        # High error rate alarm
        cloudwatch.Alarm(
            self, "HighErrorRateAlarm",
            alarm_name="fitness-coach-high-error-rate",
            alarm_description="High error rate detected across Lambda functions",
            metric=cloudwatch.Metric(
                namespace="FitnessCoach/Errors",
                metric_name="ErrorCount",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Low success rate alarm
        cloudwatch.Alarm(
            self, "LowSuccessRateAlarm",
            alarm_name="fitness-coach-low-success-rate",
            alarm_description="Low success rate for plan generation",
            metric=cloudwatch.MathExpression(
                expression="(workout_success + meal_success) / (workout_success + meal_success + errors) * 100",
                using_metrics={
                    "workout_success": cloudwatch.Metric(
                        namespace="FitnessCoach/Business",
                        metric_name="WorkoutPlanSuccess",
                        statistic="Sum",
                        period=Duration.minutes(15)
                    ),
                    "meal_success": cloudwatch.Metric(
                        namespace="FitnessCoach/Business", 
                        metric_name="MealPlanSuccess",
                        statistic="Sum",
                        period=Duration.minutes(15)
                    ),
                    "errors": cloudwatch.Metric(
                        namespace="FitnessCoach/Errors",
                        metric_name="ErrorCount",
                        statistic="Sum",
                        period=Duration.minutes(15)
                    )
                }
            ),
            threshold=80,  # 80% success rate threshold
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )