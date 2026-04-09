from django.db import models

class MealFeedback(models.Model):
    planned_meal = models.ForeignKey('planned_meal.PlannedMeal', on_delete=models.CASCADE, related_name="feedback")

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
