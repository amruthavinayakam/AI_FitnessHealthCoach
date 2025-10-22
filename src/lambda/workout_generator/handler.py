# Lambda function for workout plan generation using AWS Bedrock
import json
import logging
import os
import boto3
import asyncio
import re
import sys
from typing import Dict, Any, List
from botocore.exceptions import ClientError

# ---------- Imports from your shared layer ----------
sys.path.append('/opt/python')   # Lambda layer path
sys.path.append('../shared')     # Local dev path

try:
    from models import WorkoutPlan, DailyWorkout, Exercise, UserProfile
    from logging_utils import get_logger
except ImportError:
    import importlib.util, pathlib
    base = pathlib.Path(__file__).resolve().parents[2]
    # models
    m = importlib.util.spec_from_file_location("models", str(base / "shared" / "models.py"))
    models = importlib.util.module_from_spec(m)
    m.loader.exec_module(models)
    WorkoutPlan = models.WorkoutPlan
    DailyWorkout = models.DailyWorkout
    Exercise = models.Exercise
    UserProfile = models.UserProfile
    # logging_utils
    lu = importlib.util.spec_from_file_location("logging_utils", str(base / "shared" / "logging_utils.py"))
    logging_utils = importlib.util.module_from_spec(lu)
    lu.loader.exec_module(logging_utils)
    get_logger = logging_utils.get_logger

# Optional: Fitness MCP enrichment
try:
    from fitness_knowledge.server import FitnessKnowledgeMCPServer
except ImportError:
    FitnessKnowledgeMCPServer = None

# ---------- Logger ----------
logger = get_logger('workout-generator')

# ======================================================================
# JSON Utilities (tolerant and auto-repairing)
# ======================================================================
_TRAILING_COMMA_RE = re.compile(r",\s*(?=[}\]])")
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def _normalize_quotes(s: str) -> str:
    return (s.replace("“", '"')
             .replace("”", '"')
             .replace("‘", "'")
             .replace("’", "'")
             .replace("–", "-")
             .replace("—", "-"))

def _extract_first_json_block(text: str) -> str:
    """Extract the first JSON object from any messy text."""
    m = re.search(r'\{[\s\S]*\}', text)
    return m.group(0) if m else "{}"

def _try_parse_any_json(txt: str) -> dict:
    s = _normalize_quotes(txt.strip())
    fenced = _CODE_FENCE_RE.search(s)
    if fenced:
        s = fenced.group(1)
    s = _TRAILING_COMMA_RE.sub("", s)
    s = _extract_first_json_block(s)

    try:
        data = json.loads(s)
    except Exception as e:
        # second attempt cleanup
        s = re.sub(r"[^\x20-\x7E\n\r\t]+", "", s)
        s = _TRAILING_COMMA_RE.sub("", s)
        try:
            data = json.loads(s)
        except Exception:
            data = {}

    # Ensure expected top-level keys for downstream logic
    if "plan_type" not in data:
        data["plan_type"] = "General Fitness"
    if "duration_weeks" not in data:
        data["duration_weeks"] = 1
    if "daily_workouts" not in data or not isinstance(data["daily_workouts"], list):
        data["daily_workouts"] = []

    return data


# =======================================
# Bedrock Workout Generator (Claude model)
# =======================================
class BedrockWorkoutGenerator:
    """Generate structured workout plans via AWS Bedrock (Anthropic Claude)."""

    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime')
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '2000'))
        self.temperature = float(os.environ.get('BEDROCK_TEMPERATURE', '0.1'))
        self.top_p = float(os.environ.get('BEDROCK_TOP_P', '0.9'))
        self.enable_mcp = os.environ.get("ENABLE_FITNESS_MCP", "true").lower() == "true"
        self.fitness_mcp = FitnessKnowledgeMCPServer() if (FitnessKnowledgeMCPServer and self.enable_mcp) else None

    # ---------- Public ----------
    def generate_workout_plan(self, user_profile: UserProfile) -> WorkoutPlan:
        prompt_user, prompt_system = self._build_prompts(user_profile)

        # --- First call ---
        raw = self._call_bedrock(prompt_user, prompt_system)
        logger.info("✅ Bedrock API responded successfully.")
        logger.debug(f"Raw Bedrock output (first 400 chars): {raw[:400]}")

        try:
            data = _try_parse_any_json(raw)
        except Exception as e1:
            logger.warning(f"First parse failed ({e1}), retrying JSON-only.")
            raw2 = self._call_bedrock(
                prompt_user + "\n\nREMINDER: Return ONLY a single JSON object. No markdown, no commentary.",
                prompt_system
            )
            data = _try_parse_any_json(raw2)

        try:
            plan = self._json_to_plan(data, user_profile)
        except Exception as e:
            logger.error(f"JSON->Model conversion failed: {e}")
            return self._fallback_plan(user_profile)

        if self.fitness_mcp:
            try:
                plan = asyncio.run(self._enhance_with_mcp(plan))
            except Exception as e:
                logger.warning(f"MCP enhancement failed: {e}")

        return plan

    # ---------- Internals ----------
    def _build_prompts(self, user_profile: UserProfile):
        system = (
            "You are a JSON-only API.\n"
            "Return ONLY valid JSON matching the schema provided.\n"
            "Do not include markdown, text, or commentary.\n"
            "Response must start with '{' and end with '}'."
        )

        user = f"""
Create a 7-day workout plan for: "{user_profile.query}".

Ensure:
- Exactly 7 days (Mon–Sun)
- 4–8 exercises per day
- Each exercise includes name, sets, reps, duration, and muscle_groups.
- Respond ONLY with valid JSON matching this schema:

{{
  "plan_type": "string",
  "duration_weeks": 1,
  "daily_workouts": [
    {{
      "day": "Monday",
      "total_duration": 45,
      "notes": "Upper body focus",
      "exercises": [
        {{
          "name": "Push-ups",
          "sets": 3,
          "reps": "12-15",
          "duration": 8,
          "muscle_groups": ["chest", "triceps", "shoulders"]
        }}
      ]
    }}
  ]
}}
"""
        return user.strip(), system

    def _call_bedrock(self, user_prompt: str, system_prompt: str) -> str:
        """
        Call Bedrock API. Try structured output first; if model rejects the
        'response_format' parameter with ValidationException, retry without it.
        """
        base_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ]
        }

        # Attempt 1: with response_format (for newer Claude/Titan that support it)
        body = dict(base_body)
        body["response_format"] = {"type": "application/json"}

        try:
            resp = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            payload = json.loads(resp["body"].read())
        except ClientError as ce:
            # If the model rejects response_format, retry without it
            if ce.response.get("Error", {}).get("Code") == "ValidationException" and "response_format" in str(ce):
                body = dict(base_body)  # drop response_format
                resp = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                )
                payload = json.loads(resp["body"].read())
            else:
                raise

        # Parse text from Anthropic messages format
        text = ""
        if isinstance(payload, dict):
            if "content" in payload and isinstance(payload["content"], list) and payload["content"]:
                block = payload["content"][0]
                if isinstance(block, dict):
                    text = block.get("text", "")
            if not text:
                text = payload.get("output_text", "")

        if not text:
            raise RuntimeError("Empty or invalid Bedrock response body")
        return text

    def _json_to_plan(self, data: Dict[str, Any], user_profile: UserProfile) -> WorkoutPlan:
        # Validate top-level keys
        for k in ("plan_type", "duration_weeks", "daily_workouts"):
            if k not in data:
                raise ValueError(f"Missing key: {k}")

        valid_days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        daily: List[DailyWorkout] = []

        for day_obj in data["daily_workouts"]:
            day = day_obj.get("day", "Monday")
            if day not in valid_days:
                continue

            total_duration = int(day_obj.get("total_duration", 45))
            notes = day_obj.get("notes", "")

            exs = []
            for ex in (day_obj.get("exercises") or []):
                exs.append(Exercise(
                    name=ex.get("name", "Exercise"),
                    sets=int(ex.get("sets", 3)),
                    reps=str(ex.get("reps", "10-12")),
                    duration=int(ex.get("duration", 10)),
                    muscle_groups=[str(m).lower() for m in ex.get("muscle_groups", [])]
                ))

            # Guarantee at least one exercise to satisfy model validation
            if not exs:
                exs = [Exercise(
                    name="Rest Day (light cardio or mobility)",
                    sets=1, reps="1", duration=10, muscle_groups=["full body"]
                )]

            daily.append(DailyWorkout(
                day=day,
                exercises=exs,
                total_duration=total_duration,
                notes=notes
            ))

        if not daily:
            daily = [
                DailyWorkout(
                    day="Monday",
                    total_duration=30,
                    notes="Auto-generated fallback: insufficient Bedrock structure.",
                    exercises=[
                        Exercise(name="Bodyweight Squats", sets=3, reps="15", duration=10, muscle_groups=["legs"]),
                        Exercise(name="Push-ups", sets=3, reps="12", duration=8, muscle_groups=["chest","arms"]),
                    ]
                )
            ]

        return WorkoutPlan(
            user_id=user_profile.user_id,
            plan_type=str(data.get("plan_type", "General Fitness")),
            duration_weeks=int(data.get("duration_weeks", 1)),
            daily_workouts=daily
        )

    def _fallback_plan(self, user_profile: UserProfile) -> WorkoutPlan:
        logger.error("Falling back to minimal safe plan due to JSON parsing issues.")
        return WorkoutPlan(
            user_id=user_profile.user_id,
            plan_type="General Fitness",
            duration_weeks=1,
            daily_workouts=[
                DailyWorkout(
                    day="Monday",
                    total_duration=30,
                    notes="Fallback plan due to Bedrock parsing error.",
                    exercises=[
                        Exercise(name="Bodyweight Squats", sets=3, reps="15", duration=10, muscle_groups=["legs"]),
                        Exercise(name="Push-ups", sets=3, reps="12", duration=8, muscle_groups=["chest","arms"]),
                    ]
                )
            ]
        )

    async def _enhance_with_mcp(self, plan: WorkoutPlan) -> WorkoutPlan:
        if not self.fitness_mcp:
            return plan
        enhanced = []
        for d in plan.daily_workouts:
            upd = []
            for ex in d.exercises:
                try:
                    info = await self.fitness_mcp.get_exercise_info(ex.name)
                    if isinstance(info, dict) and "error" not in info:
                        ex.form_description = info.get("form_description")
                        ex.safety_notes = "; ".join(info.get("safety_guidelines", [])[:2])
                except Exception:
                    pass
                upd.append(ex)
            enhanced.append(DailyWorkout(day=d.day, exercises=upd, total_duration=d.total_duration, notes=d.notes))

        try:
            names = [ex.name for d in enhanced for ex in d.exercises]
            validation = await self.fitness_mcp.validate_workout_balance({"exercises": names})
            if not validation.get("balanced", True) and enhanced:
                tip = "; ".join(validation.get("recommendations", [])[:2])
                enhanced[0].notes = (enhanced[0].notes + " | " if enhanced[0].notes else "") + f"Balance recommendations: {tip}"
        except Exception:
            pass

        return WorkoutPlan(
            user_id=plan.user_id,
            plan_type=plan.plan_type,
            duration_weeks=plan.duration_weeks,
            daily_workouts=enhanced,
            created_at=plan.created_at
        )


# ==================
# Lambda entry point
# ==================
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        if 'body' not in event:
            raise ValueError("Missing request body")
        body = json.loads(event['body']) if isinstance(event['body'], str) else (event.get('body') or {})
        for f in ['username', 'userId', 'query']:
            if f not in body:
                raise ValueError(f"Missing required field: {f}")

        user_profile = UserProfile(username=body['username'], user_id=body['userId'], query=body['query'])
        generator = BedrockWorkoutGenerator()
        plan = generator.generate_workout_plan(user_profile)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'data': {
                    'workoutPlan': plan.to_dynamodb_item(),
                    'sessionId': user_profile.session_id
                },
                'message': 'Workout plan generated successfully'
            }, default=str)
        }

    except Exception as e:
        logger.error(f"Error in workout generator: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': 'Failed to generate workout plan'
            })
        }
