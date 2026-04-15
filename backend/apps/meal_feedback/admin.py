from django.contrib import admin
from apps.meal_feedback.models import MealFeedback


@admin.register(MealFeedback)
class MealFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "planned_meal", "status", "liked", "created_at")
    list_filter = ("status", "liked", "created_at")
    search_fields = ("planned_meal__meal__name", "note")
