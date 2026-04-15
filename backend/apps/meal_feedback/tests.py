import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.planned_meal.models import Meal, PlannedMeal
from apps.weekly_plan.models import WeeklyPlan


class MealFeedbackApiTests(TestCase):
    def test_log_behavior_creates_feedback_entry(self):
        user = User.objects.create_user(username="cook", password="pw123456")
        weekly_plan = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-13")
        meal = Meal.objects.create(name="Tacos")
        planned_meal = PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            meal=meal,
            day_of_week="Tuesday",
        )

        response = self.client.post(
            "/api/behavior-logs/",
            data=json.dumps(
                {
                    "planned_meal_id": planned_meal.id,
                    "status": "cooked",
                    "liked": True,
                    "note": "Would make again",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "cooked")
        self.assertEqual(planned_meal.feedback.count(), 1)
