import json
from datetime import date

from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from apps.planned_meal.models import Meal, PlannedMeal
from apps.weekly_plan.models import GroceryList, WeeklyPlan
from apps.weekly_plan.services.grocery_list import (
    build_grocery_payload,
    build_grocery_payload_for_plan,
    build_grocery_payload_from_generated_meals,
    normalize_ingredient_list,
)
from apps.weekly_plan.services.feedback import build_feedback_profile
from apps.weekly_plan.services.meal_generator import generate_weekly_meal_plan


DEFAULT_DINNER_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def _normalize_list(value):
    return normalize_ingredient_list(value)


def _serialize_meal(meal):
    if not meal:
        return None

    return {
        "id": meal.id,
        "name": meal.name,
        "description": meal.description,
        "ingredients": meal.ingredients,
        "prep_time_minutes": meal.prep_time_minutes,
        "difficulty": meal.difficulty,
    }


def _serialize_feedback(feedback):
    if not feedback:
        return None

    return {
        "id": feedback.id,
        "status": feedback.status,
        "liked": feedback.liked,
        "note": feedback.note,
        "created_at": feedback.created_at.isoformat(),
    }

def _serialize_grocery_list(weekly_plan):
    grocery_payload = build_grocery_payload_for_plan(weekly_plan)
    return {
        "items": grocery_payload["items"],
        "grouped_items": grocery_payload["grouped_items"],
    }


def _find_or_create_meal(*, name, description, ingredients, prep_time_minutes, difficulty):
    existing_meal = Meal.objects.filter(name__iexact=name).first()
    if existing_meal:
        changed = False
        if description and existing_meal.description != description:
            existing_meal.description = description
            changed = True
        if ingredients and existing_meal.ingredients != ingredients:
            existing_meal.ingredients = ingredients
            changed = True
        if prep_time_minutes and existing_meal.prep_time_minutes != prep_time_minutes:
            existing_meal.prep_time_minutes = prep_time_minutes
            changed = True
        if difficulty and existing_meal.difficulty != difficulty:
            existing_meal.difficulty = difficulty
            changed = True
        if changed:
            existing_meal.save()
        return existing_meal

    return Meal.objects.create(
        name=name,
        description=description,
        ingredients=ingredients,
        prep_time_minutes=prep_time_minutes,
        difficulty=difficulty,
    )


def _create_plan_with_generated_meals(*, user, week_start_date, notes, generated_meals):
    grocery_payload = build_grocery_payload_from_generated_meals(generated_meals)

    with transaction.atomic():
        weekly_plan = WeeklyPlan.objects.create(
            user=user,
            week_start_date=week_start_date,
            notes=notes,
        )

        for generated_meal in generated_meals:
            meal = _find_or_create_meal(
                name=generated_meal["meal"],
                description=generated_meal.get("description", ""),
                ingredients=generated_meal["ingredients"],
                prep_time_minutes=generated_meal["time"],
                difficulty=generated_meal["difficulty"],
            )
            PlannedMeal.objects.create(
                weekly_plan=weekly_plan,
                meal=meal,
                day_of_week=generated_meal["day"],
                notes=generated_meal.get("description", ""),
            )

        GroceryList.objects.create(
            weekly_plan=weekly_plan,
            items=grocery_payload["items"],
        )

    return weekly_plan


def _serialize_planned_meal(planned_meal):
    latest_feedback = planned_meal.feedback.order_by("-created_at", "-id").first()
    return {
        "id": planned_meal.id,
        "day_of_week": planned_meal.day_of_week,
        "notes": planned_meal.notes,
        "meal": _serialize_meal(planned_meal.meal),
        "latest_feedback": _serialize_feedback(latest_feedback),
    }


def serialize_plan(weekly_plan):
    grocery_list = _serialize_grocery_list(weekly_plan) if hasattr(weekly_plan, "grocery_list") else {
        "items": [],
        "grouped_items": [],
    }

    return {
        "id": weekly_plan.id,
        "user_id": weekly_plan.user_id,
        "week_start_date": weekly_plan.week_start_date.isoformat(),
        "notes": weekly_plan.notes,
        "meals": [
            _serialize_planned_meal(planned_meal)
            for planned_meal in weekly_plan.meals.select_related("meal").all()
        ],
        "grocery_list": grocery_list["items"],
        "grocery_list_grouped": grocery_list["grouped_items"],
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

    selected_meals = []
    meal_entries = []

    for meal_data in meals_data:
        meal_id = meal_data.get("meal_id")
        day_of_week = (meal_data.get("day_of_week") or "").strip()

        if not meal_id or not day_of_week:
            return JsonResponse(
                {"error": "each meal entry requires meal_id and day_of_week"},
                status=400,
            )

        try:
            meal = Meal.objects.get(pk=meal_id)
        except Meal.DoesNotExist:
            return JsonResponse({"error": f"meal {meal_id} not found"}, status=404)

        selected_meals.append(meal)
        meal_entries.append(
            {
                "meal": meal,
                "day_of_week": day_of_week,
                "notes": (meal_data.get("notes") or "").strip(),
            }
        )

    grocery_payload = build_grocery_payload(
        [
            ingredient
            for meal in selected_meals
            for ingredient in normalize_ingredient_list(meal.ingredients)
        ]
    )

    with transaction.atomic():
        weekly_plan = WeeklyPlan.objects.create(
            user=user,
            week_start_date=parsed_week_start,
            notes=notes,
        )

        for meal_entry in meal_entries:
            PlannedMeal.objects.create(
                weekly_plan=weekly_plan,
                meal=meal_entry["meal"],
                day_of_week=meal_entry["day_of_week"],
                notes=meal_entry["notes"],
            )

        GroceryList.objects.create(
            weekly_plan=weekly_plan,
            items=grocery_payload["items"],
        )

    return JsonResponse(serialize_plan(weekly_plan), status=201)


@csrf_exempt
def generate_plan(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    user_id = payload.get("user_id")
    notes = (payload.get("notes") or "").strip()
    preferences = _normalize_list(payload.get("preferences"))
    dislikes = _normalize_list(payload.get("dislikes"))
    dietary_tags = _normalize_list(payload.get("dietary_tags"))
    schedule = payload.get("schedule") if isinstance(payload.get("schedule"), (dict, list)) else {}
    max_prep_time_minutes = payload.get("max_prep_time_minutes", 30)
    week_start_date = payload.get("week_start_date")

    if not user_id:
        return JsonResponse({"error": "user_id is required"}, status=400)

    try:
        max_prep_time_minutes = int(max_prep_time_minutes)
    except (TypeError, ValueError):
        return JsonResponse({"error": "max_prep_time_minutes must be an integer"}, status=400)

    if max_prep_time_minutes <= 0:
        return JsonResponse({"error": "max_prep_time_minutes must be greater than 0"}, status=400)

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "user not found"}, status=404)

    try:
        parsed_week_start = date.fromisoformat(week_start_date) if week_start_date else date.today()
    except ValueError:
        return JsonResponse({"error": "week_start_date must be YYYY-MM-DD"}, status=400)

    recent_meals = list(
        PlannedMeal.objects.filter(weekly_plan__user=user, meal__isnull=False)
        .select_related("meal")
        .order_by("-weekly_plan__week_start_date", "-id")
        .values_list("meal__name", flat=True)[:10]
    )
    feedback_profile = build_feedback_profile(user)

    try:
        generated_meals = generate_weekly_meal_plan(
            preferences=preferences,
            dislikes=dislikes,
            dietary_tags=dietary_tags,
            recent_meals=recent_meals,
            feedback_profile=feedback_profile,
            schedule=schedule or {"days": DEFAULT_DINNER_DAYS},
            max_prep_time_minutes=max_prep_time_minutes,
            dinner_count=len(DEFAULT_DINNER_DAYS),
        )
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except ValueError as exc:
        return JsonResponse({"error": f"Unable to generate plan: {exc}"}, status=502)

    weekly_plan = _create_plan_with_generated_meals(
        user=user,
        week_start_date=parsed_week_start,
        notes=notes,
        generated_meals=generated_meals,
    )

    return JsonResponse(serialize_plan(weekly_plan), status=201)


def fetch_grocery_list(request, plan_id):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    weekly_plan = get_object_or_404(WeeklyPlan, pk=plan_id)
    grocery_list = _serialize_grocery_list(weekly_plan)

    return JsonResponse(
        {
            "plan_id": weekly_plan.id,
            "week_start_date": weekly_plan.week_start_date.isoformat(),
            "items": grocery_list["items"],
            "grouped_items": grocery_list["grouped_items"],
        }
    )


@csrf_exempt
def swap_planned_meal(request, planned_meal_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    planned_meal = get_object_or_404(
        PlannedMeal.objects.select_related("weekly_plan", "meal", "weekly_plan__user"),
        pk=planned_meal_id,
    )
    weekly_plan = planned_meal.weekly_plan

    preferences = _normalize_list(payload.get("preferences"))
    dislikes = _normalize_list(payload.get("dislikes"))
    dietary_tags = _normalize_list(payload.get("dietary_tags"))
    notes = (payload.get("notes") or "").strip()
    max_prep_time_minutes = payload.get("max_prep_time_minutes", 30)

    try:
        max_prep_time_minutes = int(max_prep_time_minutes)
    except (TypeError, ValueError):
        return JsonResponse({"error": "max_prep_time_minutes must be an integer"}, status=400)

    if max_prep_time_minutes <= 0:
        return JsonResponse({"error": "max_prep_time_minutes must be greater than 0"}, status=400)

    existing_meals = list(
        weekly_plan.meals.exclude(pk=planned_meal.pk)
        .exclude(meal__isnull=True)
        .values_list("meal__name", flat=True)
    )
    recent_meals = existing_meals + list(
        PlannedMeal.objects.filter(weekly_plan__user=weekly_plan.user, meal__isnull=False)
        .exclude(pk=planned_meal.pk)
        .select_related("meal")
        .order_by("-weekly_plan__week_start_date", "-id")
        .values_list("meal__name", flat=True)[:10]
    )
    feedback_profile = build_feedback_profile(weekly_plan.user)

    try:
        generated_meals = generate_weekly_meal_plan(
            preferences=preferences,
            dislikes=dislikes,
            dietary_tags=dietary_tags,
            recent_meals=recent_meals,
            feedback_profile=feedback_profile,
            schedule={"days": [planned_meal.day_of_week], "swap_request": planned_meal.day_of_week},
            max_prep_time_minutes=max_prep_time_minutes,
            dinner_count=1,
        )
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except ValueError as exc:
        return JsonResponse({"error": f"Unable to swap meal: {exc}"}, status=502)

    replacement = generated_meals[0]
    meal = _find_or_create_meal(
        name=replacement["meal"],
        description=replacement.get("description", ""),
        ingredients=replacement["ingredients"],
        prep_time_minutes=replacement["time"],
        difficulty=replacement["difficulty"],
    )

    with transaction.atomic():
        planned_meal.meal = meal
        planned_meal.notes = notes or replacement.get("description", "")
        planned_meal.save(update_fields=["meal", "notes"])

        grocery_payload = build_grocery_payload_for_plan(weekly_plan)
        grocery_list, _ = GroceryList.objects.get_or_create(
            weekly_plan=weekly_plan,
            defaults={"items": grocery_payload["items"]},
        )
        grocery_list.items = grocery_payload["items"]
        grocery_list.save(update_fields=["items", "updated_at"])

    return JsonResponse(
        {
            "planned_meal": _serialize_planned_meal(planned_meal),
            "grocery_list": {
                "plan_id": weekly_plan.id,
                "week_start_date": weekly_plan.week_start_date.isoformat(),
                "items": grocery_payload["items"],
                "grouped_items": grocery_payload["grouped_items"],
            },
        }
    )
