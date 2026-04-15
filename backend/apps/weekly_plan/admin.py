from django.contrib import admin
from apps.weekly_plan.models import GroceryList, WeeklyPlan


@admin.register(WeeklyPlan)
class WeeklyPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "week_start_date", "created_at")
    list_filter = ("week_start_date", "created_at")
    search_fields = ("user__username", "notes")


@admin.register(GroceryList)
class GroceryListAdmin(admin.ModelAdmin):
    list_display = ("id", "weekly_plan", "created_at", "updated_at")
    search_fields = ("weekly_plan__user__username",)
