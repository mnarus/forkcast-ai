import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from apps.planned_meal.models import Meal, PlannedMeal
from apps.weekly_plan.models import GroceryList, WeeklyPlan


class WeeklyPlanApiTests(TestCase):
    def test_create_user_endpoint_creates_user(self):
        response = self.client.post(
            "/api/users/",
            data=json.dumps(
                {
                    "username": "michelle",
                    "password": "super-secret",
                    "email": "michelle@example.com",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "michelle")
        self.assertTrue(User.objects.filter(username="michelle").exists())

    def test_fetch_meals_returns_existing_meals(self):
        meal = Meal.objects.create(
            name="Pasta Primavera",
            description="Vegetable pasta",
            ingredients=["pasta", "zucchini"],
            prep_time_minutes=25,
            difficulty="easy",
        )

        response = self.client.get("/api/meals/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meals"][0]["id"], meal.id)
        self.assertEqual(response.json()["meals"][0]["name"], meal.name)

    def test_save_plan_creates_plan_planned_meals_and_grocery_list(self):
        user = User.objects.create_user(username="planner", password="pw123456")
        meal = Meal.objects.create(
            name="Sheet Pan Salmon",
            ingredients=["salmon", "broccoli"],
            prep_time_minutes=30,
            difficulty="medium",
        )

        response = self.client.post(
            "/api/plans/",
            data=json.dumps(
                {
                    "user_id": user.id,
                    "week_start_date": "2026-04-13",
                    "notes": "Keep dinners simple",
                    "meals": [
                        {
                            "meal_id": meal.id,
                            "day_of_week": "Monday",
                            "notes": "Use frozen broccoli",
                        }
                    ],
                    "grocery_list": ["salmon", "broccoli"],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        plan = WeeklyPlan.objects.get()
        self.assertEqual(plan.user, user)
        self.assertEqual(plan.week_start_date, date(2026, 4, 13))
        self.assertEqual(plan.notes, "Keep dinners simple")
        self.assertTrue(
            PlannedMeal.objects.filter(
                weekly_plan=plan,
                meal=meal,
                day_of_week="Monday",
            ).exists()
        )
        self.assertEqual(GroceryList.objects.get(weekly_plan=plan).items, ["salmon", "broccoli"])
