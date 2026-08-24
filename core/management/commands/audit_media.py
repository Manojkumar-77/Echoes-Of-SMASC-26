import os
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Photo, HeroSlide, TimelineEvent, Student, Video, ScrapbookItem, AboutPage


class Command(BaseCommand):
    help = "Audit uploaded media files, reporting referenced files, missing files, and orphan candidates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete confirmed orphan media files from disk (default: False / read-only)",
        )

    def handle(self, *args, **options):
        delete_orphans = options.get("delete", False)
        media_root = str(settings.MEDIA_ROOT)

        self.stdout.write("==================================================")
        self.stdout.write("MEDIA FILE AUDIT & LIFECYCLE REPORT")
        self.stdout.write("==================================================")
        self.stdout.write(f"Media Root: {media_root}")

        if not os.path.exists(media_root):
            self.stdout.write(self.style.WARNING("Media root directory does not exist."))
            return

        # 1. Collect all DB-referenced file paths
        db_referenced_files = set()
        db_missing_files = set()

        def register_file(field_file):
            if not field_file or not field_file.name:
                return
            rel_path = os.path.normpath(field_file.name)
            db_referenced_files.add(rel_path)
            full_path = os.path.join(media_root, rel_path)
            if not os.path.exists(full_path):
                db_missing_files.add(rel_path)

        for p in Photo.objects.all():
            register_file(p.image)
        for h in HeroSlide.objects.all():
            register_file(h.image)
        for t in TimelineEvent.objects.all():
            register_file(t.image)
        for s in Student.objects.all():
            register_file(s.image)
        for v in Video.objects.all():
            register_file(v.video_file)
            register_file(v.thumbnail)
        for sb in ScrapbookItem.objects.all():
            register_file(sb.image)
        for ab in AboutPage.objects.all():
            register_file(ab.story_image)
            register_file(ab.creator_image)
            for photo in ab.background_photos.all():
                register_file(photo.image)

        # 2. Walk physical disk files
        disk_files = set()
        total_disk_bytes = 0

        for root, _, files in os.walk(media_root):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.normpath(os.path.relpath(full_path, media_root))
                disk_files.add(rel_path)
                total_disk_bytes += os.path.getsize(full_path)

        orphan_files = disk_files - db_referenced_files

        # 3. Output Report
        total_mb = total_disk_bytes / (1024 * 1024)
        self.stdout.write(f"Total Physical Media Files: {len(disk_files)}")
        self.stdout.write(f"Total Physical Disk Usage: {total_mb:.2f} MB")
        self.stdout.write(f"DB Referenced Files: {len(db_referenced_files)}")
        self.stdout.write(f"DB Missing Files: {len(db_missing_files)}")
        self.stdout.write(f"Orphan File Candidates: {len(orphan_files)}")

        if db_missing_files:
            self.stdout.write("\n" + self.style.WARNING("--- MISSING DB REFERENCED FILES ---"))
            for mf in sorted(db_missing_files):
                self.stdout.write(f"  [MISSING] {mf}")

        if orphan_files:
            self.stdout.write("\n" + self.style.NOTICE("--- ORPHAN CANDIDATES ---"))
            for of in sorted(orphan_files):
                self.stdout.write(f"  [ORPHAN] {of}")

            if delete_orphans:
                self.stdout.write("\n" + self.style.WARNING("Deleting orphan files..."))
                deleted_count = 0
                for of in orphan_files:
                    full_p = os.path.join(media_root, of)
                    try:
                        os.remove(full_p)
                        deleted_count += 1
                        self.stdout.write(f"  [DELETED] {of}")
                    except OSError as e:
                        self.stdout.write(self.style.ERROR(f"  [ERROR] {of}: {e}"))
                self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} orphan file(s)."))
            else:
                self.stdout.write("\nRun 'python manage.py audit_media --delete' to clean up orphan files.")
        else:
            self.stdout.write(self.style.SUCCESS("\nZero orphan files found. Disk is clean!"))

        self.stdout.write("==================================================")
