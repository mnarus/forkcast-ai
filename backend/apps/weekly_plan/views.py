import json
from datetime import date

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.planned_meal.models import Meal, PlannedMeal
from apps.weekly_plan.models import GroceryList, WeeklyPlan


def serialize_plan(weekly_plan):
    return {
        "id": weekly_plan.id,
        "user_id": weekly_plan.user_id,
        "week_start_date": weekly_plan.week_start_date.isoformat(),
        "notes": weekly_plan.notes,
        "meals": [
            {
                "id": planned_meal.id,
                "day_of_week": planned_meal.day_of_week,
                "notes": planned_meal.notes,
                "meal": (
                    {
                        "id": planned_meal.meal.id,
                        "name": planned_meal.meal.name,
                        "description": planned_meal.meal.description,
                        "ingredients": planned_meal.meal.ingredients,
                        "prep_time_minutes": planned_meal.meal.prep_time_minutes,
                        "difficulty": planned_meal.meal.difficulty,
                    }
                    if planned_meal.meal
                    else None
                ),
            }
            for planned_meal in weekly_plan.meals.select_related("meal").all()
        ],
        "grocery_list": weekly_plan.grocery_list.items if hasattr(weekly_plan, "grocery_list") else [],
    }


@csrf_exempt
def create_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    email = (payload.get("email") or "").strip()

    if not username or not password:
        return JsonResponse({"error": "username and password are required"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "username already exists"}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)

    return JsonResponse(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
        status=201,
    )


def fetch_meals(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    meals = [
        {
            "id": meal.id,
            "name": meal.name,
            "description": meal.description,
            "ingredients": meal.ingredients,
            "prep_time_minutes": meal.prep_time_minutes,
            "difficulty": meal.difficulty,
        }
        for meal in Meal.objects.all().order_by("name")
    ]
    return JsonResponse({"meals": meals})


@csrf_exempt
def save_plan(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    user_id = payload.get("user_id")
    meals_data = payload.get("meals") or []
    grocery_items = payload.get("grocery_list") or []
    notes = (payload.get("notes") or "").strip()
    week_start_date = payload.get("week_start_date")

    if not user_id:
        return JsonResponse({"error": "user_id is required"}, status=400)

    if not isinstance(meals_data, list) or not meals_data:
        return JsonResponse({"error": "meals must be a non-empty list"}, status=400)

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "user not found"}, status=404)

    try:
        parsed_week_start = (
            date.fromisoformat(week_start_date)
            if week_start_date
            else date.today()
        )
    except ValueError:
        return JsonResponse({"error": "week_start_date must be YYYY-MM-DD"}, status=400)

    weekly_plan = WeeklyPlan.objects.create(
        user=user,
        week_start_date=parsed_week_start,
        notes=notes,
    )

    for meal_data in meals_data:
        meal_id = meal_data.get("meal_id")
        day_of_week = (meal_data.get("day_of_week") or "").strip()

        if not meal_id or not day_of_week:
            weekly_plan.delete()
            return JsonResponse(
                {"error": "each meal entry requires meal_id and day_of_week"},
                status=400,
            )

        try:
            meal = Meal.objects.get(pk=meal_id)
        except Meal.DoesNotExist:
            weekly_plan.delete()
            return JsonResponse({"error": f"meal {meal_id} not found"}, status=404)

        PlannedMeal.objects.create(
            weekly_plan=weekly_plan,
            meal=meal,
            day_of_week=day_of_week,
            notes=(meal_data.get("notes") or "").strip(),
        )

    GroceryList.objects.create(
        weekly_plan=weekly_plan,
        items=grocery_items if isinstance(grocery_items, list) else [],
    )

    return JsonResponse(serialize_plan(weekly_plan), status=201)
