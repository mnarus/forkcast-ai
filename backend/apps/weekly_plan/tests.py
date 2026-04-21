import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.planned_meal.models import Meal, PlannedMeal
from apps.meal_feedback.models import MealFeedback
from apps.weekly_plan.models import GroceryList, WeeklyPlan
from apps.weekly_plan.services.grocery_list import (
    build_grocery_payload_from_generated_meals,
    build_grocery_payload_from_planned_meals,
)
from apps.weekly_plan.services.feedback import build_feedback_profile
from apps.weekly_plan.views import serialize_plan
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
            ingredients=["salmon", "broccoli", "lemon"],
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
        self.assertEqual(
            GroceryList.objects.get(weekly_plan=plan).items,
            ["salmon", "broccoli", "lemon"],
        )

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
        self.assertTrue(response.json()["grocery_list_grouped"])

        mock_generate_weekly_meal_plan.assert_called_once()
        self.assertEqual(mock_generate_weekly_meal_plan.call_args.kwargs["recent_meals"], ["Pesto Pasta"])
        self.assertEqual(mock_generate_weekly_meal_plan.call_args.kwargs["max_prep_time_minutes"], 30)
        self.assertEqual(mock_generate_weekly_meal_plan.call_args.kwargs["feedback_profile"]["history_count"], 0)

    def test_fetch_grocery_list_returns_grouped_items_for_plan(self):
        user = User.objects.create_user(username="planner5", password="pw123456")
        weekly_plan = WeeklyPlan.objects.create(user=user, week_start_date=date(2026, 4, 13))
        salmon = Meal.objects.create(
            name="Sheet Pan Salmon",
            ingredients=["salmon", "broccoli", "lemon"],
            prep_time_minutes=25,
            difficulty="easy",
        )
        quesadillas = Meal.objects.create(
            name="Veggie Quesadillas",
            ingredients=["tortillas", "bell peppers", "cheese"],
            prep_time_minutes=15,
            difficulty="easy",
        )
        PlannedMeal.objects.create(weekly_plan=weekly_plan, meal=salmon, day_of_week="Monday")
        PlannedMeal.objects.create(weekly_plan=weekly_plan, meal=quesadillas, day_of_week="Tuesday")
        GroceryList.objects.create(
            weekly_plan=weekly_plan,
            items=["placeholder"],
        )

        response = self.client.get(f"/api/plans/{weekly_plan.id}/grocery-list/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["items"],
            ["salmon", "broccoli", "lemon", "tortillas", "bell peppers", "cheese"],
        )
        produce_group = next(group for group in payload["grouped_items"] if group["category"] == "produce")
        dairy_group = next(group for group in payload["grouped_items"] if group["category"] == "dairy")
        self.assertEqual(produce_group["items"], ["bell peppers", "broccoli", "lemon"])
        self.assertEqual(dairy_group["items"], ["cheese"])

    def test_serialize_plan_includes_latest_feedback_for_each_planned_meal(self):
        user = User.objects.create_user(username="planner7", password="pw123456")
        meal = Meal.objects.create(
            name="Lemon Orzo",
            ingredients=["orzo", "lemon"],
            prep_time_minutes=20,
            difficulty="easy",
        )
        weekly_plan = WeeklyPlan.objects.create(user=user, week_start_date=date(2026, 4, 13))
        planned_meal = PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            meal=meal,
            day_of_week="Monday",
        )
        MealFeedback.objects.create(planned_meal=planned_meal, status="cooked", note="Great")
        GroceryList.objects.create(weekly_plan=weekly_plan, items=["orzo", "lemon"])

        payload = serialize_plan(weekly_plan)

        self.assertEqual(payload["meals"][0]["latest_feedback"]["status"], "cooked")
        self.assertEqual(payload["meals"][0]["latest_feedback"]["note"], "Great")

    @patch("apps.weekly_plan.views.generate_weekly_meal_plan")
    def test_swap_planned_meal_replaces_meal_and_refreshes_grocery_list(self, mock_generate_weekly_meal_plan):
        user = User.objects.create_user(username="planner8", password="pw123456")
        weekly_plan = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-13")
        current_meal = Meal.objects.create(
            name="Salmon Bowls",
            ingredients=["salmon", "rice"],
            prep_time_minutes=20,
            difficulty="easy",
        )
        side_meal = Meal.objects.create(
            name="Pasta Primavera",
            ingredients=["pasta", "zucchini"],
            prep_time_minutes=25,
            difficulty="easy",
        )
        planned_meal = PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            meal=current_meal,
            day_of_week="Monday",
        )
        PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            meal=side_meal,
            day_of_week="Tuesday",
        )
        GroceryList.objects.create(weekly_plan=weekly_plan, items=["placeholder"])

        mock_generate_weekly_meal_plan.return_value = [
            {
                "day": "Monday",
                "meal": "Chickpea Tacos",
                "description": "Fast pantry tacos.",
                "difficulty": "easy",
                "time": 15,
                "ingredients": ["chickpeas", "tortillas", "lime"],
            }
        ]

        response = self.client.post(
            f"/api/planned-meals/{planned_meal.id}/swap/",
            data=json.dumps(
                {
                    "preferences": ["quick dinners"],
                    "dislikes": ["mushrooms"],
                    "dietary_tags": ["vegetarian"],
                    "max_prep_time_minutes": 20,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        planned_meal.refresh_from_db()
        self.assertEqual(planned_meal.meal.name, "Chickpea Tacos")
        self.assertEqual(
            GroceryList.objects.get(weekly_plan=weekly_plan).items,
            ["pasta", "zucchini", "chickpeas", "tortillas", "lime"],
        )
        self.assertEqual(response.json()["planned_meal"]["meal"]["name"], "Chickpea Tacos")
        produce_group = next(
            group
            for group in response.json()["grocery_list"]["grouped_items"]
            if group["category"] == "produce"
        )
        self.assertIn("lime", produce_group["items"])
        self.assertIn("Pasta Primavera", mock_generate_weekly_meal_plan.call_args.kwargs["recent_meals"])
        self.assertEqual(mock_generate_weekly_meal_plan.call_args.kwargs["feedback_profile"]["history_count"], 0)

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


class FeedbackProfileTests(TestCase):
    def test_build_feedback_profile_applies_skip_and_repeat_penalties(self):
        user = User.objects.create_user(username="planner9", password="pw123456")
        week_one = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-06")
        week_two = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-13")

        tacos = Meal.objects.create(
            name="Tacos",
            ingredients=["tortillas", "beef", "lime"],
            prep_time_minutes=20,
            difficulty="easy",
        )
        salmon = Meal.objects.create(
            name="Salmon Rice Bowls",
            ingredients=["salmon", "rice", "cucumber"],
            prep_time_minutes=25,
            difficulty="easy",
        )

        tacos_first = PlannedMeal.objects.create(weekly_plan=week_one, meal=tacos, day_of_week="Monday")
        tacos_second = PlannedMeal.objects.create(weekly_plan=week_two, meal=tacos, day_of_week="Tuesday")
        salmon_meal = PlannedMeal.objects.create(weekly_plan=week_two, meal=salmon, day_of_week="Wednesday")

        MealFeedback.objects.create(planned_meal=tacos_first, status="skipped")
        MealFeedback.objects.create(planned_meal=tacos_second, status="skipped")
        MealFeedback.objects.create(planned_meal=salmon_meal, status="cooked", liked=True)

        profile = build_feedback_profile(user)

        weighted_meals = {item["meal"]: item["score"] for item in profile["weighted_meals"]}
        weighted_ingredients = {
            item["ingredient"]: item["score"] for item in profile["weighted_ingredients"]
        }

        self.assertEqual(profile["recent_skips"], ["Tacos", "Tacos"])
        self.assertEqual(profile["recent_repeats"], [{"meal": "Tacos", "count": 2, "penalty": 1}])
        self.assertEqual(weighted_meals["Tacos"], -7)
        self.assertEqual(weighted_meals["Salmon Rice Bowls"], 3)
        self.assertEqual(weighted_ingredients["tortillas"], -6)
        self.assertEqual(weighted_ingredients["salmon"], 3)
        self.assertIn("Salmon Rice Bowls", profile["positive_meals"])
        self.assertIn("Tacos", profile["avoid_meals"])

    @patch("apps.weekly_plan.views.generate_weekly_meal_plan")
    def test_generate_plan_passes_feedback_profile_with_behavior_weights(self, mock_generate_weekly_meal_plan):
        user = User.objects.create_user(username="planner10", password="pw123456")
        previous_plan = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-06")
        skipped_meal = Meal.objects.create(
            name="Mushroom Pasta",
            ingredients=["pasta", "mushrooms"],
            prep_time_minutes=20,
            difficulty="easy",
        )
        cooked_meal = Meal.objects.create(
            name="Lemon Chicken",
            ingredients=["chicken", "lemon"],
            prep_time_minutes=25,
            difficulty="easy",
        )
        skipped_planned_meal = PlannedMeal.objects.create(
            weekly_plan=previous_plan,
            meal=skipped_meal,
            day_of_week="Monday",
        )
        cooked_planned_meal = PlannedMeal.objects.create(
            weekly_plan=previous_plan,
            meal=cooked_meal,
            day_of_week="Tuesday",
        )
        MealFeedback.objects.create(planned_meal=skipped_planned_meal, status="skipped")
        MealFeedback.objects.create(planned_meal=cooked_planned_meal, status="cooked", liked=True)

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
            data=json.dumps({"user_id": user.id, "week_start_date": "2026-04-13"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        feedback_profile = mock_generate_weekly_meal_plan.call_args.kwargs["feedback_profile"]
        self.assertEqual(feedback_profile["history_count"], 2)
        self.assertIn("Lemon Chicken", feedback_profile["positive_meals"])
        self.assertIn("Mushroom Pasta", feedback_profile["avoid_meals"])
        self.assertIn("chicken", feedback_profile["positive_ingredients"])
        self.assertIn("mushrooms", feedback_profile["avoid_ingredients"])


class GroceryListServiceTests(TestCase):
    def test_build_grocery_payload_from_generated_meals_dedupes_and_groups_items(self):
        payload = build_grocery_payload_from_generated_meals(
            [
                {"ingredients": ["Salmon", "broccoli", "rice"]},
                {"ingredients": ["salmon", "Cheese", "broccoli"]},
            ]
        )

        self.assertEqual(payload["items"], ["Salmon", "broccoli", "rice", "Cheese"])
        labels = {group["category"]: group["items"] for group in payload["grouped_items"]}
        self.assertEqual(labels["protein"], ["Salmon"])
        self.assertEqual(labels["produce"], ["broccoli"])
        self.assertEqual(labels["grains"], ["rice"])
        self.assertEqual(labels["dairy"], ["Cheese"])

    def test_build_grocery_payload_from_planned_meals_uses_linked_meal_ingredients(self):
        user = User.objects.create_user(username="planner6", password="pw123456")
        weekly_plan = WeeklyPlan.objects.create(user=user, week_start_date="2026-04-13")
        meal = Meal.objects.create(
            name="Tofu Bowls",
            ingredients=["tofu", "spinach", "rice"],
            prep_time_minutes=20,
            difficulty="easy",
        )
        planned_meal = PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            meal=meal,
            day_of_week="Wednesday",
        )

        payload = build_grocery_payload_from_planned_meals([planned_meal])

        self.assertEqual(payload["items"], ["tofu", "spinach", "rice"])
