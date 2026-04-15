from django.contrib import admin
from apps.planned_meal.models import Meal, PlannedMeal


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "difficulty", "prep_time_minutes", "created_at")
    search_fields = ("name", "description")


@admin.register(PlannedMeal)
class PlannedMealAdmin(admin.ModelAdmin):
    list_display = ("id", "weekly_plan", "meal", "day_of_week", "notes")
    list_filter = ("day_of_week",)
    search_fields = ("meal__name", "notes")
