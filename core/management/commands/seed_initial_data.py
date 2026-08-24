import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connections
from django.db.utils import OperationalError
from core.models import HeroSlide, Student, Photo


class Command(BaseCommand):
    help = "Safely seeds initial database records only if the database is currently empty with connection warmup retry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reload initial fixtures even if database contains records.",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)

        # Connection warmup and retry logic
        db_conn = connections['default']
        connected = False
        retries = 5

        while retries > 0 and not connected:
            try:
                db_conn.ensure_connection()
                connected = True
            except OperationalError:
                retries -= 1
                self.stdout.write("Database warming up... retrying in 2 seconds.")
                time.sleep(2)

        if not connected:
            self.stdout.write(self.style.ERROR("Could not establish database connection. Skipping seeding."))
            return

        try:
            has_data = (
                HeroSlide.objects.exists()
                or Student.objects.exists()
                or Photo.objects.exists()
            )

            if has_data and not force:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Database already contains CMS data. Skipping initial fixture load to preserve production content."
                    )
                )
                return

            self.stdout.write("Fresh database detected. Loading initial fixture 'initial_data.json'...")
            call_command("loaddata", "initial_data.json", ignorenonexistent=True)
            self.stdout.write(self.style.SUCCESS("Initial fixtures loaded successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Initial fixture loading encountered an issue: {e}"))
