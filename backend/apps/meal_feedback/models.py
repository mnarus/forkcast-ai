from django.db import models
from apps.planned_meal.models import PlannedMeal


class MealFeedback(models.Model):
    planned_meal = models.ForeignKey(PlannedMeal, on_delete=models.CASCADE, related_name="feedback")

    status = models.CharField(
        max_length=20,
        choices=[
            ("cooked", "Cooked"),
            ("skipped", "Skipped"),
        ],
        blank=True,
    )

    liked = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
