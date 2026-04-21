import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.planned_meal.models import Meal, PlannedMeal
from apps.weekly_plan.models import GroceryList, WeeklyPlan
from apps.weekly_plan.services.meal_generator import _validate_generated_meals


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

    @patch("apps.weekly_plan.views.generate_weekly_meal_plan")
    def test_generate_plan_creates_weekly_plan_from_llm_output(self, mock_generate_weekly_meal_plan):
        user = User.objects.create_user(username="planner2", password="pw123456")
        previous_plan = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-06")
        previous_meal = Meal.objects.create(
            name="Pesto Pasta",
            ingredients=["pasta", "pesto"],
            prep_time_minutes=20,
            difficulty="easy",
        )
        PlannedMeal.objects.create(
            weekly_plan=previous_plan,
            meal=previous_meal,
            day_of_week="Monday",
        )

        mock_generate_weekly_meal_plan.return_value = [
            {
                "day": "Monday",
                "meal": "Sheet Pan Salmon",
                "description": "Fast salmon with roasted vegetables.",
                "difficulty": "easy",
                "time": 25,
                "ingredients": ["salmon", "broccoli", "lemon"],
            },
            {
                "day": "Tuesday",
                "meal": "Turkey Taco Bowls",
                "description": "Ground turkey bowls with rice and salsa.",
                "difficulty": "easy",
                "time": 20,
                "ingredients": ["ground turkey", "rice", "salsa"],
            },
            {
                "day": "Wednesday",
                "meal": "Chickpea Curry",
                "description": "Pantry-friendly curry with spinach.",
                "difficulty": "medium",
                "time": 30,
                "ingredients": ["chickpeas", "coconut milk", "spinach"],
            },
            {
                "day": "Thursday",
                "meal": "Veggie Quesadillas",
                "description": "Crisp tortillas with peppers and cheese.",
                "difficulty": "easy",
                "time": 15,
                "ingredients": ["tortillas", "bell peppers", "cheese"],
            },
            {
                "day": "Friday",
                "meal": "Sesame Tofu Noodles",
                "description": "Quick noodles with tofu and snap peas.",
                "difficulty": "medium",
                "time": 25,
                "ingredients": ["tofu", "noodles", "snap peas"],
            },
        ]

        response = self.client.post(
            "/api/plans/generate/",
            data=json.dumps(
                {
                    "user_id": user.id,
                    "week_start_date": "2026-04-13",
                    "notes": "Weeknight dinners only",
                    "preferences": ["high protein", "low stress"],
                    "dislikes": ["mushrooms"],
                    "dietary_tags": ["pescatarian-flexible"],
                    "schedule": {"busy_days": ["Tuesday", "Thursday"]},
                    "max_prep_time_minutes": 30,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        created_plan = WeeklyPlan.objects.get(week_start_date="2026-04-13")
        self.assertEqual(created_plan.notes, "Weeknight dinners only")
        self.assertEqual(created_plan.meals.count(), 5)
        self.assertEqual(created_plan.grocery_list.items[0], "salmon")
        self.assertIn("snap peas", created_plan.grocery_list.items)
        self.assertTrue(Meal.objects.filter(name="Sheet Pan Salmon").exists())

        mock_generate_weekly_meal_plan.assert_called_once()
        self.assertEqual(mock_generate_weekly_meal_plan.call_args.kwargs["recent_meals"], ["Pesto Pasta"])
        self.assertEqual(mock_generate_weekly_meal_plan.call_args.kwargs["max_prep_time_minutes"], 30)

    @patch("apps.weekly_plan.views.generate_weekly_meal_plan")
    def test_generate_plan_returns_upstream_generation_errors(self, mock_generate_weekly_meal_plan):
        user = User.objects.create_user(username="planner3", password="pw123456")
        mock_generate_weekly_meal_plan.side_effect = ValueError("duplicate meal found")

        response = self.client.post(
            "/api/plans/generate/",
            data=json.dumps({"user_id": user.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("Unable to generate plan", response.json()["error"])

    def test_generate_plan_validates_max_prep_time(self):
        user = User.objects.create_user(username="planner4", password="pw123456")

        response = self.client.post(
            "/api/plans/generate/",
            data=json.dumps(
                {
                    "user_id": user.id,
                    "max_prep_time_minutes": 0,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "max_prep_time_minutes must be greater than 0",
        )


class MealGeneratorValidationTests(TestCase):
    def test_validate_generated_meals_rejects_disliked_ingredient(self):
        with self.assertRaisesMessage(ValueError, "conflicts with dislikes"):
            _validate_generated_meals(
                [
                    {
                        "day": "Monday",
                        "meal": "Mushroom Pasta",
                        "description": "Creamy pasta night.",
                        "difficulty": "easy",
                        "time": 20,
                        "ingredients": ["pasta", "mushrooms"],
                    },
                    {
                        "day": "Tuesday",
                        "meal": "Taco Bowls",
                        "description": "Fast taco bowl.",
                        "difficulty": "easy",
                        "time": 20,
                        "ingredients": ["rice", "beans"],
                    },
                    {
                        "day": "Wednesday",
                        "meal": "Salmon Rice",
                        "description": "Quick salmon dinner.",
                        "difficulty": "easy",
                        "time": 20,
                        "ingredients": ["salmon", "rice"],
                    },
                    {
                        "day": "Thursday",
                        "meal": "Tofu Stir Fry",
                        "description": "Simple tofu and vegetables.",
                        "difficulty": "easy",
                        "time": 20,
                        "ingredients": ["tofu", "broccoli"],
                    },
                    {
                        "day": "Friday",
                        "meal": "Quesadillas",
                        "description": "Cheesy quesadilla night.",
                        "difficulty": "easy",
                        "time": 20,
                        "ingredients": ["tortillas", "cheese"],
                    },
                ],
                dinner_count=5,
                max_prep_time_minutes=30,
                dislikes=["mushrooms"],
            )
