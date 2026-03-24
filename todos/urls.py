from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("settings/", views.settings, name="settings"),
    path("api/me/", views.api_me, name="api_me"),
    path("api/universities/", views.api_universities, name="api_universities"),
    path("api/profile/", views.api_profile_update, name="api_profile_update"),
    path("api/tasks/", views.api_tasks, name="api_tasks"),
    path("api/tasks/<int:task_id>/", views.api_task_detail, name="api_task_detail"),
    path("api/reminders/today/", views.api_reminders_today, name="api_reminders_today"),
    path(
        "api/reminders/mark-shown/",
        views.api_reminders_mark_shown,
        name="api_reminders_mark_shown",
    ),
]

