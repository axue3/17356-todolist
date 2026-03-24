from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):  # noqa: ANN001, ANN201
    if not created:
        return
    UserProfile.objects.create(user=instance)

