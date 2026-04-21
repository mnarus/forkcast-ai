from collections import Counter, defaultdict

from apps.meal_feedback.models import MealFeedback


POSITIVE_STATUS_WEIGHT = {
    MealFeedback.COOKED: 2,
}
NEGATIVE_STATUS_WEIGHT = {
    MealFeedback.SKIPPED: -3,
}
LIKED_BONUS = 1
REPEAT_PENALTY = 1


def build_feedback_profile(user, *, history_limit=25):
    feedback_entries = list(
        MealFeedback.objects.filter(planned_meal__weekly_plan__user=user, planned_meal__meal__isnull=False)
        .select_related("planned_meal__meal", "planned_meal__weekly_plan")
        .order_by("-created_at", "-id")[:history_limit]
    )

    meal_counts = Counter()
    meal_scores = defaultdict(int)
    ingredient_scores = defaultdict(int)
    recent_skips = []
    recent_repeats = []

    for feedback in feedback_entries:
        meal = feedback.planned_meal.meal
        meal_name = meal.name.strip()
        normalized_name = meal_name.lower()
        meal_counts[normalized_name] += 1

        score = POSITIVE_STATUS_WEIGHT.get(feedback.status, 0) + NEGATIVE_STATUS_WEIGHT.get(
            feedback.status,
            0,
        )
        if feedback.liked is True:
            score += LIKED_BONUS
        elif feedback.liked is False:
            score -= LIKED_BONUS

        meal_scores[meal_name] += score
        for ingredient in meal.ingredients or []:
            normalized_ingredient = str(ingredient).strip()
            if normalized_ingredient:
                ingredient_scores[normalized_ingredient] += score

        if feedback.status == MealFeedback.SKIPPED:
            recent_skips.append(meal_name)

    for meal_name, count in meal_counts.items():
        if count > 1:
            canonical_name = next(
                original_name
                for original_name in meal_scores
                if original_name.lower() == meal_name
            )
            penalty = (count - 1) * REPEAT_PENALTY
            meal_scores[canonical_name] -= penalty
            recent_repeats.append({"meal": canonical_name, "count": count, "penalty": penalty})

    weighted_meals = sorted(
        (
            {"meal": meal_name, "score": score}
            for meal_name, score in meal_scores.items()
            if score != 0
        ),
        key=lambda item: (-item["score"], item["meal"].lower()),
    )
    weighted_ingredients = sorted(
        (
            {"ingredient": ingredient, "score": score}
            for ingredient, score in ingredient_scores.items()
            if score != 0
        ),
        key=lambda item: (-item["score"], item["ingredient"].lower()),
    )

    positive_meals = [item["meal"] for item in weighted_meals if item["score"] > 0][:5]
    avoid_meals = [item["meal"] for item in weighted_meals if item["score"] < 0][:5]
    positive_ingredients = [
        item["ingredient"] for item in weighted_ingredients if item["score"] > 0
    ][:8]
    avoid_ingredients = [item["ingredient"] for item in weighted_ingredients if item["score"] < 0][
        :8
    ]

    return {
        "weighted_meals": weighted_meals,
        "weighted_ingredients": weighted_ingredients,
        "positive_meals": positive_meals,
        "avoid_meals": avoid_meals,
        "positive_ingredients": positive_ingredients,
        "avoid_ingredients": avoid_ingredients,
        "recent_skips": recent_skips[:5],
        "recent_repeats": recent_repeats[:5],
        "history_count": len(feedback_entries),
    }
