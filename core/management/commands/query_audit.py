from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from django.db import connection, reset_queries
from django.test import RequestFactory


class Command(BaseCommand):
    help = "Audit DB query counts for all public views"

    def handle(self, *args, **options):
        django_settings.DEBUG = True
        from core.views import home, gallery, timeline, scrapbook, yearbook, videos, about, contact

        rf = RequestFactory()
        views_to_check = [
            ("home", home, "/"),
            ("gallery", gallery, "/gallery/"),
            ("timeline", timeline, "/timeline/"),
            ("scrapbook", scrapbook, "/scrapbook/"),
            ("yearbook", yearbook, "/yearbook/"),
            ("videos", videos, "/videos/"),
            ("about", about, "/about/"),
            ("contact", contact, "/contact/"),
        ]

        self.stdout.write("==================================================")
        self.stdout.write("DATABASE QUERY COUNT & PERFORMANCE AUDIT")
        self.stdout.write("==================================================")

        for name, view_fn, url in views_to_check:
            reset_queries()
            req = rf.get(url)
            req.session = {}
            try:
                view_fn(req)
            except Exception as e:
                self.stderr.write(f"  ERROR in {name}: {e}")
                continue

            count = len(connection.queries)
            self.stdout.write(f"\nVIEW: {name:12s}  QUERIES: {count}")
            for i, q in enumerate(connection.queries):
                self.stdout.write(f"  [{i+1:2d}] {q['time']}s  {q['sql'][:180]}")
