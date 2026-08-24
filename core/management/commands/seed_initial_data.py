from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import HeroSlide, Student, Photo


class Command(BaseCommand):
    help = "Safely seeds initial database records only if the database is currently empty. Prevents overwriting production CMS edits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reload initial fixtures even if database contains records.",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)

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
        try:
            call_command("loaddata", "initial_data.json", ignorenonexistent=True)
            self.stdout.write(self.style.SUCCESS("Initial fixtures loaded successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load initial fixture: {e}"))
