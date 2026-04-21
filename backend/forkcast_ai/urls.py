"""
URL configuration for forkcast_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from apps.meal_feedback.views import log_behavior
from apps.weekly_plan.views import (
    create_user,
    fetch_grocery_list,
    fetch_meals,
    generate_plan,
    save_plan,
    swap_planned_meal,
)
from .views import hello_world

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/hello/', hello_world, name='hello-world'),
    path('api/users/', create_user, name='create-user'),
    path('api/meals/', fetch_meals, name='fetch-meals'),
    path('api/plans/', save_plan, name='save-plan'),
    path('api/plans/generate/', generate_plan, name='generate-plan'),
    path('api/plans/<int:plan_id>/grocery-list/', fetch_grocery_list, name='fetch-grocery-list'),
    path('api/planned-meals/<int:planned_meal_id>/swap/', swap_planned_meal, name='swap-planned-meal'),
    path('api/behavior-logs/', log_behavior, name='log-behavior'),
]
