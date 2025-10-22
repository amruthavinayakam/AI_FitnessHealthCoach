# Custom Fitness Knowledge MCP Server
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class EquipmentType(Enum):
    BODYWEIGHT = "bodyweight"
    DUMBBELLS = "dumbbells"
    BARBELL = "barbell"
    RESISTANCE_BANDS = "resistance_bands"
    MACHINE = "machine"
    KETTLEBELL = "kettlebell"
    CABLE = "cable"

@dataclass
class Exercise:
    name: str
    muscle_groups: List[str]
    equipment: EquipmentType
    difficulty: DifficultyLevel
    form_description: str
    safety_guidelines: List[str]
    progression_tips: List[str]
    common_mistakes: List[str]
    rep_ranges: Dict[str, str]  # beginner, intermediate, advanced
    sets_recommendation: Dict[str, int]

@dataclass
class WorkoutProgression:
    current_level: DifficultyLevel
    next_exercises: List[str]
    progression_timeline: str
    volume_increase: Dict[str, Any]

class FitnessKnowledgeMCPServer:
    """
    MCP Server providing exercise database and fitness expertise
    """
    
    def __init__(self):
        self.exercise_db = self._initialize_exercise_database()
        self.muscle_group_mapping = self._initialize_muscle_groups()
        self.progression_paths = self._initialize_progression_paths()
    
    def _initialize_exercise_database(self) -> Dict[str, Exercise]:
        """Initialize comprehensive exercise database"""
        exercises = {
            # Chest Exercises
            "push_up": Exercise(
                name="Push-up",
                muscle_groups=["chest", "triceps", "shoulders", "core"],
                equipment=EquipmentType.BODYWEIGHT,
                difficulty=DifficultyLevel.BEGINNER,
                form_description="Start in plank position with hands slightly wider than shoulders. Lower body until chest nearly touches ground, then push back up maintaining straight line from head to heels.",
                safety_guidelines=[
                    "Keep core engaged throughout movement",
                    "Maintain straight line from head to heels",
                    "Don't let hips sag or pike up",
                    "Control the descent - don't drop down"
                ],
                progression_tips=[
                    "Start with incline push-ups if regular is too difficult",
                    "Progress to decline push-ups for increased difficulty",
                    "Add pause at bottom for increased time under tension"
                ],
                common_mistakes=[
                    "Partial range of motion",
                    "Flaring elbows too wide",
                    "Not engaging core properly"
                ],
                rep_ranges={"beginner": "5-10", "intermediate": "10-20", "advanced": "20-30+"},
                sets_recommendation={"beginner": 2, "intermediate": 3, "advanced": 4}
            ),
            
            "bench_press": Exercise(
                name="Bench Press",
                muscle_groups=["chest", "triceps", "shoulders"],
                equipment=EquipmentType.BARBELL,
                difficulty=DifficultyLevel.INTERMEDIATE,
                form_description="Lie on bench with feet flat on floor. Grip bar slightly wider than shoulders. Lower bar to chest with control, then press up explosively.",
                safety_guidelines=[
                    "Always use a spotter for heavy weights",
                    "Keep feet planted on floor",
                    "Maintain natural arch in lower back",
                    "Don't bounce bar off chest"
                ],
                progression_tips=[
                    "Start with empty barbell to learn form",
                    "Increase weight gradually (2.5-5lbs per week)",
                    "Focus on controlled eccentric phase"
                ],
                common_mistakes=[
                    "Bouncing bar off chest",
                    "Lifting feet off ground",
                    "Uneven bar path"
                ],
                rep_ranges={"beginner": "8-12", "intermediate": "6-10", "advanced": "4-8"},
                sets_recommendation={"beginner": 3, "intermediate": 4, "advanced": 5}
            ),
            
            # Back Exercises
            "pull_up": Exercise(
                name="Pull-up",
                muscle_groups=["lats", "rhomboids", "biceps", "rear_delts"],
                equipment=EquipmentType.BODYWEIGHT,
                difficulty=DifficultyLevel.INTERMEDIATE,
                form_description="Hang from bar with overhand grip, hands shoulder-width apart. Pull body up until chin clears bar, then lower with control.",
                safety_guidelines=[
                    "Start with assisted pull-ups if needed",
                    "Don't swing or use momentum",
                    "Full range of motion - dead hang to chin over bar",
                    "Engage core to prevent swinging"
                ],
                progression_tips=[
                    "Use resistance bands for assistance",
                    "Practice negative pull-ups",
                    "Build up with lat pulldowns first"
                ],
                common_mistakes=[
                    "Using momentum to swing up",
                    "Partial range of motion",
                    "Not engaging lats properly"
                ],
                rep_ranges={"beginner": "1-5", "intermediate": "5-12", "advanced": "12-20+"},
                sets_recommendation={"beginner": 3, "intermediate": 4, "advanced": 5}
            ),
            
            "deadlift": Exercise(
                name="Deadlift",
                muscle_groups=["hamstrings", "glutes", "erector_spinae", "traps", "lats"],
                equipment=EquipmentType.BARBELL,
                difficulty=DifficultyLevel.ADVANCED,
                form_description="Stand with feet hip-width apart, bar over mid-foot. Hinge at hips, grip bar, keep chest up and back straight. Drive through heels to stand up.",
                safety_guidelines=[
                    "Master hip hinge movement pattern first",
                    "Keep bar close to body throughout lift",
                    "Maintain neutral spine - no rounding",
                    "Start with light weight to learn form"
                ],
                progression_tips=[
                    "Practice with Romanian deadlifts first",
                    "Use trap bar for easier learning curve",
                    "Focus on hip hinge mobility"
                ],
                common_mistakes=[
                    "Rounding the back",
                    "Bar drifting away from body",
                    "Not engaging lats to keep bar close"
                ],
                rep_ranges={"beginner": "5-8", "intermediate": "3-6", "advanced": "1-5"},
                sets_recommendation={"beginner": 3, "intermediate": 4, "advanced": 5}
            ),
            
            # Leg Exercises
            "squat": Exercise(
                name="Squat",
                muscle_groups=["quadriceps", "glutes", "hamstrings", "core"],
                equipment=EquipmentType.BODYWEIGHT,
                difficulty=DifficultyLevel.BEGINNER,
                form_description="Stand with feet shoulder-width apart. Lower body by bending knees and hips, keeping chest up. Descend until thighs parallel to ground, then drive up.",
                safety_guidelines=[
                    "Keep knees tracking over toes",
                    "Maintain upright torso",
                    "Don't let knees cave inward",
                    "Full depth - thighs parallel or below"
                ],
                progression_tips=[
                    "Start with bodyweight, progress to goblet squats",
                    "Work on ankle and hip mobility",
                    "Add weight gradually"
                ],
                common_mistakes=[
                    "Knees caving inward",
                    "Forward lean of torso",
                    "Not reaching proper depth"
                ],
                rep_ranges={"beginner": "10-15", "intermediate": "8-12", "advanced": "6-10"},
                sets_recommendation={"beginner": 3, "intermediate": 4, "advanced": 5}
            ),
            
            # Shoulder Exercises
            "overhead_press": Exercise(
                name="Overhead Press",
                muscle_groups=["shoulders", "triceps", "core"],
                equipment=EquipmentType.BARBELL,
                difficulty=DifficultyLevel.INTERMEDIATE,
                form_description="Stand with feet hip-width apart, bar at shoulder level. Press bar straight up overhead, keeping core tight. Lower with control.",
                safety_guidelines=[
                    "Keep core engaged throughout",
                    "Don't arch back excessively",
                    "Press bar in straight line overhead",
                    "Warm up shoulders thoroughly"
                ],
                progression_tips=[
                    "Start with dumbbell shoulder press",
                    "Work on shoulder mobility",
                    "Practice with empty barbell first"
                ],
                common_mistakes=[
                    "Excessive back arch",
                    "Pressing bar forward instead of up",
                    "Not engaging core"
                ],
                rep_ranges={"beginner": "8-12", "intermediate": "6-10", "advanced": "4-8"},
                sets_recommendation={"beginner": 3, "intermediate": 4, "advanced": 5}
            )
        }
        
        return exercises
    
    def _initialize_muscle_groups(self) -> Dict[str, List[str]]:
        """Initialize muscle group categories for balanced workout planning"""
        return {
            "push": ["chest", "triceps", "shoulders"],
            "pull": ["lats", "rhomboids", "biceps", "rear_delts", "traps"],
            "legs": ["quadriceps", "hamstrings", "glutes", "calves"],
            "core": ["abs", "obliques", "erector_spinae"],
            "upper_body": ["chest", "lats", "shoulders", "triceps", "biceps"],
            "lower_body": ["quadriceps", "hamstrings", "glutes", "calves"]
        }
    
    def _initialize_progression_paths(self) -> Dict[str, List[str]]:
        """Initialize exercise progression paths from beginner to advanced"""
        return {
            "push_progression": ["push_up", "incline_push_up", "decline_push_up", "bench_press"],
            "pull_progression": ["assisted_pull_up", "negative_pull_up", "pull_up", "weighted_pull_up"],
            "squat_progression": ["squat", "goblet_squat", "front_squat", "back_squat"],
            "deadlift_progression": ["romanian_deadlift", "trap_bar_deadlift", "deadlift"]
        }
    
    async def get_exercise_info(self, exercise_name: str) -> Dict[str, Any]:
        """Get detailed exercise information including form and safety"""
        exercise_key = exercise_name.lower().replace(" ", "_").replace("-", "_")
        exercise = self.exercise_db.get(exercise_key)
        
        if exercise:
            return {
                "name": exercise.name,
                "muscle_groups": exercise.muscle_groups,
                "equipment": exercise.equipment.value,
                "difficulty": exercise.difficulty.value,
                "form_description": exercise.form_description,
                "safety_guidelines": exercise.safety_guidelines,
                "progression_tips": exercise.progression_tips,
                "common_mistakes": exercise.common_mistakes,
                "rep_ranges": exercise.rep_ranges,
                "sets_recommendation": exercise.sets_recommendation
            }
        return {"error": f"Exercise '{exercise_name}' not found in database"}
    
    async def suggest_workout_progression(self, current_plan: Dict, user_level: str) -> Dict[str, Any]:
        """Suggest workout progression based on user level and current plan"""
        try:
            level = DifficultyLevel(user_level.lower())
        except ValueError:
            return {"error": "Invalid user level. Use: beginner, intermediate, or advanced"}
        
        suggestions = {
            "progression_recommendations": [],
            "volume_adjustments": {},
            "new_exercises": [],
            "timeline": "4-6 weeks"
        }
        
        # Analyze current exercises and suggest progressions
        current_exercises = current_plan.get("exercises", [])
        
        for exercise_name in current_exercises:
            exercise_key = exercise_name.lower().replace(" ", "_")
            exercise = self.exercise_db.get(exercise_key)
            
            if exercise:
                # Suggest progression based on current difficulty vs user level
                if exercise.difficulty == DifficultyLevel.BEGINNER and level != DifficultyLevel.BEGINNER:
                    suggestions["progression_recommendations"].append({
                        "current_exercise": exercise.name,
                        "progression": self._get_next_progression(exercise_key),
                        "reason": "Ready for increased difficulty"
                    })
                
                # Volume adjustments
                if level == DifficultyLevel.BEGINNER:
                    suggestions["volume_adjustments"][exercise.name] = {
                        "sets": exercise.sets_recommendation["beginner"],
                        "reps": exercise.rep_ranges["beginner"]
                    }
                elif level == DifficultyLevel.INTERMEDIATE:
                    suggestions["volume_adjustments"][exercise.name] = {
                        "sets": exercise.sets_recommendation["intermediate"],
                        "reps": exercise.rep_ranges["intermediate"]
                    }
                else:  # Advanced
                    suggestions["volume_adjustments"][exercise.name] = {
                        "sets": exercise.sets_recommendation["advanced"],
                        "reps": exercise.rep_ranges["advanced"]
                    }
        
        # Suggest muscle group balance
        muscle_groups_covered = self._analyze_muscle_group_coverage(current_exercises)
        missing_groups = self._identify_missing_muscle_groups(muscle_groups_covered)
        
        for group in missing_groups:
            exercise_suggestions = self._get_exercises_for_muscle_group(group, level)
            suggestions["new_exercises"].extend(exercise_suggestions)
        
        return suggestions
    
    def _get_next_progression(self, exercise_key: str) -> Optional[str]:
        """Get the next exercise in progression path"""
        for progression_name, exercises in self.progression_paths.items():
            if exercise_key in exercises:
                current_index = exercises.index(exercise_key)
                if current_index < len(exercises) - 1:
                    return exercises[current_index + 1]
        return None
    
    def _analyze_muscle_group_coverage(self, exercises: List[str]) -> List[str]:
        """Analyze which muscle groups are covered by current exercises"""
        covered_groups = set()
        
        for exercise_name in exercises:
            exercise_key = exercise_name.lower().replace(" ", "_")
            exercise = self.exercise_db.get(exercise_key)
            if exercise:
                covered_groups.update(exercise.muscle_groups)
        
        return list(covered_groups)
    
    def _identify_missing_muscle_groups(self, covered_groups: List[str]) -> List[str]:
        """Identify muscle groups that need more attention"""
        essential_groups = ["chest", "lats", "shoulders", "quadriceps", "hamstrings", "glutes"]
        missing = []
        
        for group in essential_groups:
            if group not in covered_groups:
                missing.append(group)
        
        return missing
    
    def _get_exercises_for_muscle_group(self, muscle_group: str, level: DifficultyLevel) -> List[Dict[str, str]]:
        """Get exercise recommendations for specific muscle group and level"""
        recommendations = []
        
        for exercise_key, exercise in self.exercise_db.items():
            if (muscle_group in exercise.muscle_groups and 
                exercise.difficulty == level):
                recommendations.append({
                    "exercise": exercise.name,
                    "reason": f"Targets {muscle_group}",
                    "difficulty": exercise.difficulty.value
                })
        
        return recommendations[:2]  # Limit to 2 suggestions per muscle group
    
    async def validate_workout_balance(self, workout_plan: Dict) -> Dict[str, Any]:
        """Validate workout plan for muscle group balance and safety"""
        exercises = workout_plan.get("exercises", [])
        
        # Analyze muscle group distribution
        muscle_group_count = {}
        total_volume = {"push": 0, "pull": 0, "legs": 0}
        
        for exercise_name in exercises:
            exercise_key = exercise_name.lower().replace(" ", "_")
            exercise = self.exercise_db.get(exercise_key)
            
            if exercise:
                for group in exercise.muscle_groups:
                    muscle_group_count[group] = muscle_group_count.get(group, 0) + 1
                
                # Calculate volume distribution
                if any(g in self.muscle_group_mapping["push"] for g in exercise.muscle_groups):
                    total_volume["push"] += 1
                if any(g in self.muscle_group_mapping["pull"] for g in exercise.muscle_groups):
                    total_volume["pull"] += 1
                if any(g in self.muscle_group_mapping["legs"] for g in exercise.muscle_groups):
                    total_volume["legs"] += 1
        
        # Check for imbalances
        warnings = []
        recommendations = []
        
        # Push/Pull ratio check
        if total_volume["push"] > 0 and total_volume["pull"] > 0:
            ratio = total_volume["push"] / total_volume["pull"]
            if ratio > 1.5:
                warnings.append("Too much pushing vs pulling - risk of shoulder imbalance")
                recommendations.append("Add more pulling exercises (rows, pull-ups)")
            elif ratio < 0.67:
                warnings.append("Too much pulling vs pushing - consider balance")
                recommendations.append("Add more pushing exercises (push-ups, presses)")
        
        # Check for missing major muscle groups
        essential_groups = ["chest", "lats", "quadriceps", "hamstrings"]
        missing_groups = [g for g in essential_groups if g not in muscle_group_count]
        
        if missing_groups:
            warnings.append(f"Missing major muscle groups: {', '.join(missing_groups)}")
            for group in missing_groups:
                exercises_for_group = self._get_exercises_for_muscle_group(group, DifficultyLevel.BEGINNER)
                recommendations.extend([ex["exercise"] for ex in exercises_for_group])
        
        return {
            "balanced": len(warnings) == 0,
            "muscle_group_distribution": muscle_group_count,
            "volume_distribution": total_volume,
            "warnings": warnings,
            "recommendations": recommendations
        }

    async def get_exercise_by_muscle_group(self, muscle_group: str, difficulty: str = "beginner") -> Dict[str, Any]:
        """Get exercises targeting specific muscle group"""
        try:
            level = DifficultyLevel(difficulty.lower())
        except ValueError:
            level = DifficultyLevel.BEGINNER
        
        matching_exercises = []
        
        for exercise_key, exercise in self.exercise_db.items():
            if (muscle_group.lower() in [mg.lower() for mg in exercise.muscle_groups] and
                exercise.difficulty == level):
                matching_exercises.append({
                    "name": exercise.name,
                    "equipment": exercise.equipment.value,
                    "form_description": exercise.form_description,
                    "safety_guidelines": exercise.safety_guidelines[:2]  # Top 2 safety tips
                })
        
        return {
            "muscle_group": muscle_group,
            "difficulty": level.value,
            "exercises": matching_exercises,
            "count": len(matching_exercises)
        }
    
    async def get_workout_safety_check(self, exercises: List[str]) -> Dict[str, Any]:
        """Perform safety check on workout combination"""
        safety_issues = []
        recommendations = []
        
        # Check for overuse of same muscle groups
        muscle_usage = {}
        equipment_needed = set()
        
        for exercise_name in exercises:
            exercise_key = exercise_name.lower().replace(" ", "_")
            exercise = self.exercise_db.get(exercise_key)
            
            if exercise:
                equipment_needed.add(exercise.equipment.value)
                
                for muscle in exercise.muscle_groups:
                    muscle_usage[muscle] = muscle_usage.get(muscle, 0) + 1
        
        # Check for muscle overuse
        for muscle, count in muscle_usage.items():
            if count > 3:
                safety_issues.append(f"Potential overuse of {muscle} - appears in {count} exercises")
                recommendations.append(f"Consider reducing {muscle} exercises or adding rest between them")
        
        # Check for equipment diversity
        if len(equipment_needed) == 1 and "bodyweight" not in equipment_needed:
            recommendations.append("Consider adding bodyweight alternatives for equipment-free options")
        
        return {
            "safe": len(safety_issues) == 0,
            "safety_issues": safety_issues,
            "recommendations": recommendations,
            "equipment_needed": list(equipment_needed),
            "muscle_usage": muscle_usage
        }

# MCP Server Protocol Integration
async def main():
    """Main function to run the MCP server"""
    server = FitnessKnowledgeMCPServer()
    
    # Example usage - in production this would be integrated with MCP protocol
    print("Fitness Knowledge MCP Server initialized")
    print(f"Exercise database contains {len(server.exercise_db)} exercises")
    
    # Test functionality
    test_exercise = await server.get_exercise_info("push_up")
    print(f"Test exercise info: {test_exercise['name']}")
    
    test_progression = await server.suggest_workout_progression(
        {"exercises": ["push_up", "squat"]}, 
        "beginner"
    )
    print(f"Progression suggestions: {len(test_progression['progression_recommendations'])} recommendations")

if __name__ == "__main__":
    asyncio.run(main())