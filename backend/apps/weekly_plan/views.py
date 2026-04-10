from apps.weekly_plan.models import WeeklyPlan
from apps.planned_meal.models import PlannedMeal
from django.utils import timezone


def create_weekly_plan(user, meals_data):
    weekly_plan = WeeklyPlan.objects.create(
        user=user,
        week_start_date=timezone.now().date()
    )

    day_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
    }

    for meal in meals_data:
        PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            day_of_week=day_map.get(meal["day"], 0),
            name=meal["meal"],
            difficulty=meal.get("difficulty", ""),
            estimated_time=meal.get("time"),
            ingredients=meal.get("ingredients", []),
        )

    return weekly_plan