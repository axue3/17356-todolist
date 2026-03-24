from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .models import ReminderLog, Task, University, UserProfile


User = get_user_model()

@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html")


@login_required
def settings(request: HttpRequest) -> HttpResponse:
    return render(request, "settings.html")


def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log them in by creating a session.
            from django.contrib.auth import login

            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "registration.html", {"form": form})


def _get_profile(request: HttpRequest) -> UserProfile:
    # Be defensive: under edge cases (e.g., partial migrations / manual DB edits),
    # the UserProfile row might not exist.
    try:
        return UserProfile.objects.select_related("university").get(user=request.user)
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user)
        return UserProfile.objects.select_related("university").get(user=request.user)


def _get_local_now(profile: UserProfile) -> datetime:
    tz_name = profile.timezone or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def _require_university(profile: UserProfile) -> University:
    if not profile.university_id:
        raise ValueError("No university selected")
    return profile.university


@require_http_methods(["GET"])
@login_required
def api_me(request: HttpRequest) -> JsonResponse:
    profile = _get_profile(request)
    universities = list(University.objects.all().order_by("name").values("id", "name"))

    current = None
    if profile.university_id:
        current = {"id": profile.university_id, "name": profile.university.name}

    return JsonResponse(
        {
            "user": {"id": request.user.id, "username": request.user.username},
            "profile": {
                "university": current,
                "timezone": profile.timezone,
                "reminder_enabled": profile.reminder_enabled,
                "morning_hour": profile.morning_hour,
            },
            "universities": universities,
        }
    )


@require_http_methods(["GET"])
@login_required
def api_universities(request: HttpRequest) -> JsonResponse:
    universities = list(University.objects.all().order_by("name").values("id", "name"))
    return JsonResponse({"universities": universities})


@require_http_methods(["POST"])
@login_required
def api_profile_update(request: HttpRequest) -> JsonResponse:
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    profile = _get_profile(request)

    university_id = body.get("university_id")
    timezone = body.get("timezone")
    reminder_enabled = body.get("reminder_enabled")
    morning_hour = body.get("morning_hour")

    if university_id is None:
        return JsonResponse({"error": "university_id is required"}, status=400)
    try:
        university_id = int(university_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "university_id must be an integer"}, status=400)

    university = University.objects.filter(id=university_id).first()
    if not university:
        return JsonResponse({"error": "Unknown university"}, status=400)

    if timezone is not None:
        # Store string; validation happens during reminder calculations.
        if not isinstance(timezone, str) or not timezone:
            return JsonResponse({"error": "timezone must be a string"}, status=400)

    if reminder_enabled is not None and not isinstance(reminder_enabled, bool):
        return JsonResponse({"error": "reminder_enabled must be boolean"}, status=400)

    if morning_hour is not None:
        try:
            morning_hour = int(morning_hour)
        except (TypeError, ValueError):
            return JsonResponse({"error": "morning_hour must be an integer"}, status=400)
        if morning_hour < 0 or morning_hour > 23:
            return JsonResponse({"error": "morning_hour must be 0-23"}, status=400)

    profile.university = university
    if timezone is not None:
        profile.timezone = timezone
    if reminder_enabled is not None:
        profile.reminder_enabled = reminder_enabled
    if morning_hour is not None:
        profile.morning_hour = morning_hour
    profile.save()

    return JsonResponse({"ok": True})


@require_http_methods(["GET", "POST"])
@login_required
def api_tasks(request: HttpRequest) -> JsonResponse:
    profile = _get_profile(request)
    try:
        university = _require_university(profile)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    if request.method == "GET":
        tasks = list(
            Task.objects.filter(user=request.user, university=university)
            .order_by("due_date", "created_at")
            .values("id", "title", "due_date", "completed")
        )
        return JsonResponse({"tasks": tasks})

    # POST create
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    title = body.get("title")
    due_date_raw = body.get("due_date")
    if not isinstance(title, str) or not title.strip():
        return JsonResponse({"error": "title is required"}, status=400)
    title = title.strip()
    if len(title) > 300:
        return JsonResponse({"error": "title is too long"}, status=400)

    if not isinstance(due_date_raw, str):
        return JsonResponse({"error": "due_date is required (YYYY-MM-DD)"}, status=400)
    due_date = parse_date(due_date_raw)
    if not due_date:
        return JsonResponse({"error": "due_date must be YYYY-MM-DD"}, status=400)

    try:
        task = Task.objects.create(
            user=request.user,
            university=university,
            title=title,
            due_date=due_date,
            completed=False,
        )
    except IntegrityError:
        return JsonResponse({"error": "Failed to create task"}, status=400)
    except Exception:
        return JsonResponse({"error": "Failed to create task"}, status=500)

    return JsonResponse(
        {"task": {"id": task.id, "title": task.title, "due_date": str(task.due_date), "completed": task.completed}},
        status=201,
    )


@require_http_methods(["PATCH", "DELETE"])
@login_required
def api_task_detail(request: HttpRequest, task_id: int) -> JsonResponse:
    profile = _get_profile(request)
    try:
        university = _require_university(profile)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    task = Task.objects.filter(id=task_id, user=request.user, university=university).first()
    if not task:
        return JsonResponse({"error": "Task not found"}, status=404)

    if request.method == "DELETE":
        task.delete()
        return JsonResponse({"ok": True})

    # PATCH
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    changed = False
    title = body.get("title", None)
    due_date_raw = body.get("due_date", None)
    completed = body.get("completed", None)

    if title is not None:
        if not isinstance(title, str) or not title.strip():
            return JsonResponse({"error": "title must be a non-empty string"}, status=400)
        task.title = title.strip()
        changed = True

    if due_date_raw is not None:
        if not isinstance(due_date_raw, str):
            return JsonResponse({"error": "due_date must be YYYY-MM-DD"}, status=400)
        due_date = parse_date(due_date_raw)
        if not due_date:
            return JsonResponse({"error": "due_date must be YYYY-MM-DD"}, status=400)
        task.due_date = due_date
        changed = True

    if completed is not None:
        if not isinstance(completed, bool):
            return JsonResponse({"error": "completed must be boolean"}, status=400)
        task.completed = completed
        changed = True

    if changed:
        task.save()

    return JsonResponse(
        {"task": {"id": task.id, "title": task.title, "due_date": str(task.due_date), "completed": task.completed}}
    )


@require_http_methods(["GET"])
@login_required
def api_reminders_today(request: HttpRequest) -> JsonResponse:
    profile = _get_profile(request)

    try:
        university = _require_university(profile)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    now = _get_local_now(profile)
    today = now.date()
    hour = now.hour

    reminder_date_exists = ReminderLog.objects.filter(
        user=request.user, university=university, reminder_date=today
    ).exists()

    tasks = list(
        Task.objects.filter(
            user=request.user, university=university, due_date=today, completed=False
        ).order_by("created_at").values("id", "title", "due_date", "completed")
    )

    should_show = False
    if profile.reminder_enabled and not reminder_date_exists and tasks:
        start = profile.morning_hour
        end = (profile.morning_hour + 2) % 24
        if profile.morning_hour <= 21:
            should_show = start <= hour < (start + 2)
        else:
            # Handle wrap around midnight.
            should_show = hour >= start or hour < end

        # Create the log immediately so the reminder can't show repeatedly
        # (even if the user reloads before clicking "Got it").
        if should_show:
            ReminderLog.objects.get_or_create(
                user=request.user,
                university=university,
                reminder_date=today,
            )

    return JsonResponse({"should_show": should_show, "tasks": tasks})


@require_http_methods(["POST"])
@login_required
def api_reminders_mark_shown(request: HttpRequest) -> JsonResponse:
    profile = _get_profile(request)
    try:
        university = _require_university(profile)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    now = _get_local_now(profile)
    today = now.date()

    reminder_date_exists = ReminderLog.objects.filter(
        user=request.user, university=university, reminder_date=today
    ).exists()
    if reminder_date_exists:
        return JsonResponse({"ok": True})

    if not profile.reminder_enabled:
        return JsonResponse({"error": "Reminders are disabled"}, status=400)

    tasks_due_today_exists = Task.objects.filter(
        user=request.user, university=university, due_date=today, completed=False
    ).exists()
    if not tasks_due_today_exists:
        return JsonResponse({"error": "No tasks due today"}, status=400)

    hour = now.hour
    start = profile.morning_hour
    end = (profile.morning_hour + 2) % 24
    if profile.morning_hour <= 21:
        in_window = start <= hour < (start + 2)
    else:
        in_window = hour >= start or hour < end

    if not in_window:
        return JsonResponse({"error": "Not in reminder window"}, status=400)

    ReminderLog.objects.get_or_create(
        user=request.user,
        university=university,
        reminder_date=today,
    )
    return JsonResponse({"ok": True})

