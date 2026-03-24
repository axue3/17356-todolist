from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db import IntegrityError
from django.utils.text import slugify


class University(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    def save(self, *args, **kwargs):  # noqa: ANN002
        old_slug = None
        candidate_slug = slugify(self.name) if self.name else ""

        if self.pk:
            old = University.objects.filter(pk=self.pk).only("name", "slug").first()
            if old and old.name != self.name and candidate_slug:
                old_slug = self.slug
                self.slug = candidate_slug
        else:
            if not self.slug and candidate_slug:
                self.slug = candidate_slug

        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            # If the candidate slug collides with another University,
            # fall back to the previous slug (when available).
            if old_slug:
                self.slug = old_slug
                super().save(*args, **kwargs)
            else:
                raise

    def __str__(self) -> str:
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)

    # Reminder settings are stored in the user's local timezone.
    timezone = models.CharField(max_length=60, default="America/New_York")
    reminder_enabled = models.BooleanField(default=True)
    morning_hour = models.PositiveSmallIntegerField(default=8)  # 0-23

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile({self.user_id})"


class Task(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    university = models.ForeignKey(University, on_delete=models.CASCADE)

    title = models.CharField(max_length=300)
    due_date = models.DateField()
    completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "university", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"Task({self.id}): {self.title}"


class ReminderLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    reminder_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "university", "reminder_date"],
                name="unique_reminder_log_per_day",
            )
        ]

