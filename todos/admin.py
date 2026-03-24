from django.contrib import admin
from .models import University, UserProfile, Task, ReminderLog


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "slug"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "university", "timezone", "reminder_enabled", "morning_hour"]
    list_select_related = ["university", "user"]
    search_fields = ["user__username", "university__name"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "university", "title", "due_date", "completed", "created_at"]
    list_filter = ["due_date", "completed", "university"]
    search_fields = ["title", "user__username"]
    list_select_related = ["user", "university"]


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "university", "reminder_date", "created_at"]
    list_filter = ["reminder_date", "university"]
    search_fields = ["user__username", "university__name"]
    list_select_related = ["user", "university"]

