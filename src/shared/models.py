"""
Data models for the Fitness Health Coach system.

This module contains all data models with proper type hints, validation,
and serialization/deserialization methods for DynamoDB integration.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import uuid
from decimal import Decimal


@dataclass
class UserProfile:
    """User profile containing identification and fitness preferences."""
    
    username: str
    user_id: str
    query: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate user profile data after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate user profile fields."""
        if not self.username or not self.username.strip():
            raise ValueError("Username cannot be empty")
        
        if not self.user_id or not self.user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        
        if len(self.query) > 1000:
            raise ValueError("Query cannot exceed 1000 characters")
        
        # Sanitize inputs
        self.username = self.username.strip()
        self.user_id = self.user_id.strip()
        self.query = self.query.strip()
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        return {
            'userId': self.user_id,
            'sessionId': self.session_id,
            'username': self.username,
            'query': self.query,
            'timestamp': Decimal(str(self.timestamp.timestamp())),
            'ttl': Decimal(str((self.timestamp.timestamp() + 86400)))  # 24 hours TTL
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'UserProfile':
        """Create UserProfile from DynamoDB item."""
        return cls(
            username=item['username'],
            user_id=item['userId'],
            query=item['query'],
            session_id=item['sessionId'],
            timestamp=datetime.fromtimestamp(float(item['timestamp']))
        )


@dataclass
class Exercise:
    """Individual exercise with details."""
    
    name: str
    sets: int
    reps: str
    duration: int  # in minutes
    muscle_groups: List[str]
    form_description: Optional[str] = None
    safety_notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate exercise data."""
        self._validate()
    
    def _validate(self):
        """Validate exercise fields."""
        if not self.name or not self.name.strip():
            raise ValueError("Exercise name cannot be empty")
        
        if self.sets < 0:
            raise ValueError("Sets must be non-negative")
        
        if self.duration < 0:
            raise ValueError("Duration must be non-negative")
        
        if not self.muscle_groups:
            raise ValueError("At least one muscle group must be specified")
        
        # Sanitize inputs
        self.name = self.name.strip()
        self.muscle_groups = [mg.strip() for mg in self.muscle_groups if mg.strip()]


@dataclass
class DailyWorkout:
    """Daily workout containing multiple exercises."""
    
    day: str
    exercises: List[Exercise]
    total_duration: int  # in minutes
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate daily workout data."""
        self._validate()
    
    def _validate(self):
        """Validate daily workout fields."""
        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        if self.day not in valid_days:
            raise ValueError(f"Day must be one of: {', '.join(valid_days)}")
        
        if not self.exercises:
            raise ValueError("Daily workout must contain at least one exercise")
        
        if self.total_duration < 0:
            raise ValueError("Total duration must be non-negative")
    
    def calculate_total_duration(self) -> int:
        """Calculate total duration from exercises."""
        return sum(exercise.duration for exercise in self.exercises)


@dataclass
class WorkoutPlan:
    """Complete workout plan for a user."""
    
    user_id: str
    plan_type: str
    duration_weeks: int
    daily_workouts: List[DailyWorkout]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate workout plan data."""
        self._validate()
    
    def _validate(self):
        """Validate workout plan fields."""
        if not self.user_id or not self.user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        if not self.plan_type or not self.plan_type.strip():
            raise ValueError("Plan type cannot be empty")
        
        if self.duration_weeks <= 0:
            raise ValueError("Duration must be positive")
        
        if not self.daily_workouts:
            raise ValueError("Workout plan must contain daily workouts")
        
        if len(self.daily_workouts) > 7:
            raise ValueError("Weekly plan cannot have more than 7 days")
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        return {
            'userId': self.user_id,
            'planType': self.plan_type,
            'durationWeeks': self.duration_weeks,
            'dailyWorkouts': [
                {
                    'day': workout.day,
                    'totalDuration': workout.total_duration,
                    'notes': workout.notes,
                    'exercises': [
                        {
                            'name': ex.name,
                            'sets': ex.sets,
                            'reps': ex.reps,
                            'duration': ex.duration,
                            'muscleGroups': ex.muscle_groups,
                            'formDescription': ex.form_description,
                            'safetyNotes': ex.safety_notes
                        }
                        for ex in workout.exercises
                    ]
                }
                for workout in self.daily_workouts
            ],
            'createdAt': Decimal(str(self.created_at.timestamp()))
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'WorkoutPlan':
        """Create WorkoutPlan from DynamoDB item."""
        daily_workouts = []
        for workout_data in item['dailyWorkouts']:
            exercises = []
            for ex_data in workout_data['exercises']:
                exercise = Exercise(
                    name=ex_data['name'],
                    sets=ex_data['sets'],
                    reps=ex_data['reps'],
                    duration=ex_data['duration'],
                    muscle_groups=ex_data['muscleGroups'],
                    form_description=ex_data.get('formDescription'),
                    safety_notes=ex_data.get('safetyNotes')
                )
                exercises.append(exercise)
            
            daily_workout = DailyWorkout(
                day=workout_data['day'],
                exercises=exercises,
                total_duration=workout_data['totalDuration'],
                notes=workout_data.get('notes')
            )
            daily_workouts.append(daily_workout)
        
        return cls(
            user_id=item['userId'],
            plan_type=item['planType'],
            duration_weeks=item['durationWeeks'],
            daily_workouts=daily_workouts,
            created_at=datetime.fromtimestamp(float(item['createdAt']))
        )


@dataclass
class Meal:
    """Individual meal with nutritional information."""
    
    recipe_id: int
    title: str
    calories: int
    protein: float  # in grams
    carbs: float    # in grams
    fat: float      # in grams
    prep_time: int  # in minutes
    ingredients: Optional[List[str]] = None
    instructions: Optional[str] = None
    
    def __post_init__(self):
        """Validate meal data."""
        self._validate()
    
    def _validate(self):
        """Validate meal fields."""
        if self.recipe_id <= 0:
            raise ValueError("Recipe ID must be positive")
        
        if not self.title or not self.title.strip():
            raise ValueError("Meal title cannot be empty")
        
        if self.calories < 0:
            raise ValueError("Calories must be non-negative")
        
        if self.protein < 0 or self.carbs < 0 or self.fat < 0:
            raise ValueError("Macronutrients must be non-negative")
        
        if self.prep_time < 0:
            raise ValueError("Prep time must be non-negative")
        
        # Sanitize inputs
        self.title = self.title.strip()


@dataclass
class DailyMeals:
    """Daily meal plan with breakfast, lunch, and dinner."""
    
    date: str  # YYYY-MM-DD format
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    snacks: Optional[List[Meal]] = None
    
    def __post_init__(self):
        """Validate daily meals data."""
        self._validate()
    
    def _validate(self):
        """Validate daily meals fields."""
        # Validate date format
        try:
            datetime.strptime(self.date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
    
    def calculate_total_calories(self) -> int:
        """Calculate total calories for the day."""
        total = self.breakfast.calories + self.lunch.calories + self.dinner.calories
        if self.snacks:
            total += sum(snack.calories for snack in self.snacks)
        return total
    
    def calculate_total_macros(self) -> Dict[str, float]:
        """Calculate total macronutrients for the day."""
        total_protein = self.breakfast.protein + self.lunch.protein + self.dinner.protein
        total_carbs = self.breakfast.carbs + self.lunch.carbs + self.dinner.carbs
        total_fat = self.breakfast.fat + self.lunch.fat + self.dinner.fat
        
        if self.snacks:
            total_protein += sum(snack.protein for snack in self.snacks)
            total_carbs += sum(snack.carbs for snack in self.snacks)
            total_fat += sum(snack.fat for snack in self.snacks)
        
        return {
            'protein': total_protein,
            'carbs': total_carbs,
            'fat': total_fat
        }


@dataclass
class MealPlan:
    """Complete meal plan for a user."""
    
    user_id: str
    week_start: str  # YYYY-MM-DD format
    daily_meals: List[DailyMeals]
    total_calories: int
    dietary_preferences: Optional[List[str]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate meal plan data."""
        self._validate()
    
    def _validate(self):
        """Validate meal plan fields."""
        if not self.user_id or not self.user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        # Validate week_start date format
        try:
            datetime.strptime(self.week_start, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Week start must be in YYYY-MM-DD format")
        
        if not self.daily_meals:
            raise ValueError("Meal plan must contain daily meals")
        
        if len(self.daily_meals) > 7:
            raise ValueError("Weekly meal plan cannot have more than 7 days")
        
        if self.total_calories < 0:
            raise ValueError("Total calories must be non-negative")
    
    def calculate_weekly_calories(self) -> int:
        """Calculate total calories for the week."""
        return sum(day.calculate_total_calories() for day in self.daily_meals)
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        return {
            'userId': self.user_id,
            'weekStart': self.week_start,
            'totalCalories': self.total_calories,
            'dietaryPreferences': self.dietary_preferences or [],
            'dailyMeals': [
                {
                    'date': day.date,
                    'breakfast': self._meal_to_dict(day.breakfast),
                    'lunch': self._meal_to_dict(day.lunch),
                    'dinner': self._meal_to_dict(day.dinner),
                    'snacks': [self._meal_to_dict(snack) for snack in day.snacks] if day.snacks else []
                }
                for day in self.daily_meals
            ],
            'createdAt': Decimal(str(self.created_at.timestamp()))
        }
    
    def _meal_to_dict(self, meal: Meal) -> Dict[str, Any]:
        """Convert meal to dictionary format."""
        return {
            'recipeId': meal.recipe_id,
            'title': meal.title,
            'calories': meal.calories,
            'protein': Decimal(str(meal.protein)),
            'carbs': Decimal(str(meal.carbs)),
            'fat': Decimal(str(meal.fat)),
            'prepTime': meal.prep_time,
            'ingredients': meal.ingredients or [],
            'instructions': meal.instructions
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'MealPlan':
        """Create MealPlan from DynamoDB item."""
        daily_meals = []
        for day_data in item['dailyMeals']:
            breakfast = cls._meal_from_dict(day_data['breakfast'])
            lunch = cls._meal_from_dict(day_data['lunch'])
            dinner = cls._meal_from_dict(day_data['dinner'])
            
            snacks = None
            if day_data.get('snacks'):
                snacks = [cls._meal_from_dict(snack_data) for snack_data in day_data['snacks']]
            
            daily_meal = DailyMeals(
                date=day_data['date'],
                breakfast=breakfast,
                lunch=lunch,
                dinner=dinner,
                snacks=snacks
            )
            daily_meals.append(daily_meal)
        
        return cls(
            user_id=item['userId'],
            week_start=item['weekStart'],
            daily_meals=daily_meals,
            total_calories=item['totalCalories'],
            dietary_preferences=item.get('dietaryPreferences', []),
            created_at=datetime.fromtimestamp(float(item['createdAt']))
        )
    
    @classmethod
    def _meal_from_dict(cls, meal_data: Dict[str, Any]) -> Meal:
        """Create Meal from dictionary format."""
        return Meal(
            recipe_id=meal_data['recipeId'],
            title=meal_data['title'],
            calories=meal_data['calories'],
            protein=float(meal_data['protein']),
            carbs=float(meal_data['carbs']),
            fat=float(meal_data['fat']),
            prep_time=meal_data['prepTime'],
            ingredients=meal_data.get('ingredients'),
            instructions=meal_data.get('instructions')
        )


# Validation utilities
def validate_user_input(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate user input data and return any validation errors.
    
    Args:
        data: Dictionary containing user input data
        
    Returns:
        Dictionary of field names to error messages
    """
    errors = {}
    
    # Validate required fields
    required_fields = ['username', 'userId', 'query']
    for field in required_fields:
        if field not in data or not data[field] or not str(data[field]).strip():
            errors[field] = f"{field} is required and cannot be empty"
    
    # Validate field lengths and formats
    if 'username' in data and data['username']:
        username = str(data['username']).strip()
        if len(username) > 50:
            errors['username'] = "Username cannot exceed 50 characters"
        elif len(username) < 3:
            errors['username'] = "Username must be at least 3 characters"
    
    if 'userId' in data and data['userId']:
        user_id = str(data['userId']).strip()
        if len(user_id) > 100:
            errors['userId'] = "User ID cannot exceed 100 characters"
    
    if 'query' in data and data['query']:
        query = str(data['query']).strip()
        if len(query) > 1000:
            errors['query'] = "Query cannot exceed 1000 characters"
        elif len(query) < 10:
            errors['query'] = "Query must be at least 10 characters"
    
    return errors


def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize user input data to prevent security vulnerabilities.
    
    Args:
        data: Dictionary containing user input data
        
    Returns:
        Sanitized data dictionary
    """
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Strip whitespace and remove potentially harmful characters
            sanitized_value = value.strip()
            # Remove null bytes and control characters
            sanitized_value = ''.join(char for char in sanitized_value if ord(char) >= 32 or char in '\t\n\r')
            sanitized[key] = sanitized_value
        else:
            sanitized[key] = value
    
    return sanitized