import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.meal_feedback.models import MealFeedback
from apps.planned_meal.models import PlannedMeal


@csrf_exempt
def log_behavior(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    planned_meal_id = payload.get("planned_meal_id")
    status = payload.get("status")
    liked = payload.get("liked")
    note = (payload.get("note") or "").strip()

    if not planned_meal_id or status not in {choice[0] for choice in MealFeedback.STATUS_CHOICES}:
        return JsonResponse(
            {"error": "planned_meal_id and a valid status are required"},
            status=400,
        )

    try:
        planned_meal = PlannedMeal.objects.get(pk=planned_meal_id)
    except PlannedMeal.DoesNotExist:
        return JsonResponse({"error": "planned meal not found"}, status=404)

    behavior_log = MealFeedback.objects.create(
        planned_meal=planned_meal,
        status=status,
        liked=liked if isinstance(liked, bool) else None,
        note=note,
    )

    return JsonResponse(
        {
            "id": behavior_log.id,
            "planned_meal_id": behavior_log.planned_meal_id,
            "status": behavior_log.status,
            "liked": behavior_log.liked,
            "note": behavior_log.note,
            "created_at": behavior_log.created_at.isoformat(),
        },
        status=201,
    )
