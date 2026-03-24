import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create a superuser if it does not already exist"

    def handle(self, *args, **options):
        username = os.environ.get("SU_USERNAME")
        email = os.environ.get("SU_EMAIL")
        password = os.environ.get("SU_PASSWORD")

        if not username or not email or not password:
            self.stdout.write(self.style.WARNING("Superuser environment variables not set."))
            return

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS("Superuser already exists."))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(self.style.SUCCESS("Superuser created successfully."))
