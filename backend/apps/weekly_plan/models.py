from django.db import models
from django.contrib.auth.models import User


class WeeklyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GroceryList(models.Model):
    weekly_plan = models.OneToOneField(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="grocery_list",
    )
    items = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
