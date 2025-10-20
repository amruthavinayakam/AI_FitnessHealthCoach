#!/usr/bin/env python3
"""
AWS CDK App for Fitness Health Coach System
"""
import aws_cdk as cdk
from fitness_coach_stack import FitnessCoachStack

app = cdk.App()

# Create the main stack
FitnessCoachStack(
    app, 
    "FitnessCoachStack",
    description="Fitness Health Coach - AWS Serverless Chatbot System"
)

app.synth()