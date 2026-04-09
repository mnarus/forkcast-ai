from django.db import models
from . import WeeklyPlan

class PlannedMeal(models.Model):
    weekly_plan = models.ForeignKey(WeeklyPlan, on_delete=models.CASCADE, related_name="meals")
    day_of_week = models.CharField(max_length=10)

    name = models.CharField(max_length=255)

    difficulty = models.CharField(max_length=20, blank=True)
    estimated_time = models.IntegerField(null=True, blank=True)

