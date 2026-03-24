from django.core.management.base import BaseCommand

from todos.models import University


UNIVERSITIES = [
    "Carnegie Mellon University",
    "Stanford University",
    "University of California, Berkeley",
    "Massachusetts Institute of Technology",
    "University of Michigan",
    "Harvard University",
    "Princeton University",
    "Columbia University",
]


class Command(BaseCommand):
    help = "Seed default university options for university designation selection."

    def handle(self, *args, **options):  # noqa: ANN002, ANN201
        created = 0
        for name in UNIVERSITIES:
            _, was_created = University.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded universities (created {created})."))

