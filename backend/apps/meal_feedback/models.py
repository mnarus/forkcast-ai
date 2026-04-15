from django.db import models
from apps.planned_meal.models import PlannedMeal


class MealFeedback(models.Model):
    COOKED = "cooked"
    SKIPPED = "skipped"
    STATUS_CHOICES = [
        (COOKED, "Cooked"),
        (SKIPPED, "Skipped"),
    ]

    planned_meal = models.ForeignKey(PlannedMeal, on_delete=models.CASCADE, related_name="feedback")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
    )
    liked = models.BooleanField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
