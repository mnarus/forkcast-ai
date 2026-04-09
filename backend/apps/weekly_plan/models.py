from django.db import models
from django.contrib.auth.models import User

class WeeklyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)