from django.db import models
from apps.weekly_plan.models import WeeklyPlan


class Meal(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ingredients = models.JSONField(default=list, blank=True)
    prep_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PlannedMeal(models.Model):
    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="meals",
    )
    meal = models.ForeignKey(
        Meal,
        on_delete=models.CASCADE,
        related_name="planned_instances",
        null=True,
        blank=True,
    )
    day_of_week = models.CharField(max_length=10)
    notes = models.CharField(max_length=255, blank=True)

