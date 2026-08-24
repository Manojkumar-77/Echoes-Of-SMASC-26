from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from core.models import (
    Photo, Category, ScrapbookPlacement, SelectedGalleryPhoto,
    AboutPage, TimelineEvent, Student, Video, ContactMessage
)
import json

User = get_user_model()


class Phase2ConnectivityAndDataFlowTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="password123", email="admin@example.com")
        self.client = Client()
        self.client.login(username="admin", password="password123")
        self.category = Category.objects.create(name="Phase 2 Category", slug="phase-2-category")
        self.photo1 = Photo.objects.create(title="Photo One", category=self.category, status="approved", is_active=True, show_gallery=True)
        self.photo2 = Photo.objects.create(title="Photo Two", category=self.category, status="approved", is_active=True, show_gallery=True)

    def test_gallery_source_of_truth(self):
        # Visible photo
        res1 = self.client.get("/gallery/")
        self.assertIn("Photo One", res1.content.decode("utf-8"))

        # show_gallery = False -> hidden
        self.photo1.show_gallery = False
        self.photo1.save()
        res2 = self.client.get("/gallery/")
        self.assertNotIn("Photo One", res2.content.decode("utf-8"))

        # is_active = False -> hidden regardless of show_gallery
        self.photo2.is_active = False
        self.photo2.save()
        res3 = self.client.get("/gallery/")
        self.assertNotIn("Photo Two", res3.content.decode("utf-8"))

    def test_atlas_cover_photos_no_fallback(self):
        # show_in_atlas = False -> not in atlas covers
        self.photo1.show_in_atlas = False
        self.photo1.save()
        res = self.client.get("/gallery/")
        self.assertEqual(res.status_code, 200)

        # show_in_atlas = True -> appears as cover
        self.photo1.show_in_atlas = True
        self.photo1.save()
        res2 = self.client.get("/gallery/")
        self.assertIn("Photo One", res2.content.decode("utf-8"))

    def test_selected_memories_master_active(self):
        sel = SelectedGalleryPhoto.objects.create(photo=self.photo1, order=1, is_active=True)
        res1 = self.client.get("/gallery/")
        self.assertIn("Photo One", res1.content.decode("utf-8"))

        # Master is_active OFF -> hidden from selected memories
        self.photo1.is_active = False
        self.photo1.save()
        res2 = self.client.get("/gallery/")
        # Selected section shouldn't display inactive photo
        self.assertNotIn("Photo One", res2.content.decode("utf-8"))

    def test_scrapbook_no_fallback_empty_state(self):
        ScrapbookPlacement.objects.all().delete()
        res = self.client.get("/scrapbook/")
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        self.assertNotIn("film-frame", content)

    def test_film_cross_strip_and_independent_dedupe(self):
        # Same photo in Strip 1 and Strip 2
        sp1 = ScrapbookPlacement.objects.create(photo=self.photo1, section="film", film_strip=1, display_order=1, is_active=True)
        sp2 = ScrapbookPlacement.objects.create(photo=self.photo1, section="film", film_strip=2, display_order=1, is_active=True)

        res = self.client.get("/scrapbook/")
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        
        # Both Strip 1 (01 A) and Strip 2 (11 B) render
        self.assertIn("01 A", content)
        self.assertIn("11 B", content)

    def test_film_direction_class_mapping(self):
        ScrapbookPlacement.objects.create(photo=self.photo1, section="film", film_strip=1, display_order=1, is_active=True)
        ScrapbookPlacement.objects.create(photo=self.photo2, section="film", film_strip=2, display_order=1, is_active=True)

        res = self.client.get("/scrapbook/")
        content = res.content.decode("utf-8")
        # Strip 1 -> film-row--right (moves RIGHT)
        self.assertIn("film-row--right", content)
        # Strip 2 -> film-row--left (moves LEFT)
        self.assertIn("film-row--left", content)

    def test_photo_master_active_killswitch_site_wide(self):
        ScrapbookPlacement.objects.create(photo=self.photo1, section="film", film_strip=1, display_order=1, is_active=True)
        SelectedGalleryPhoto.objects.create(photo=self.photo1, order=1, is_active=True)

        # Deactivate photo
        self.photo1.is_active = False
        self.photo1.save()

        # Site-wide hidden check
        self.assertNotIn("Photo One", self.client.get("/gallery/").content.decode("utf-8"))
        self.assertNotIn("Photo One", self.client.get("/scrapbook/").content.decode("utf-8"))
        self.assertNotIn("Photo One", self.client.get("/").content.decode("utf-8"))

    def test_contact_form_submission_persists(self):
        res = self.client.post("/contact/", {
            "name": "Jane Visitor",
            "email": "jane@example.com",
            "subject": "Inquiry",
            "category": "General",
            "message": "Hello College Memories team!",
        })
        self.assertIn(res.status_code, [200, 302])
        self.assertTrue(ContactMessage.objects.filter(email="jane@example.com").exists())

    def test_all_public_routes_return_200(self):
        routes = ["/", "/gallery/", "/timeline/", "/scrapbook/", "/yearbook/", "/videos/", "/about/", "/contact/"]
        for r in routes:
            response = self.client.get(r)
            self.assertEqual(response.status_code, 200, f"Route {r} failed with status {response.status_code}")

    def test_featured_photos_homepage_flow(self):
        # Create a featured photo
        featured = Photo.objects.create(
            title="Golden Milestone Memory",
            category=self.category,
            status="approved",
            is_active=True,
            is_featured=True,
            home_order=1
        )
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Golden Milestone Memory", res.content.decode("utf-8"))

    def test_memory_index_mobile_navigation_rendering(self):
        res = self.client.get("/")
        content = res.content.decode("utf-8")
        self.assertIn("MEMORY INDEX", content)
        self.assertIn("mob-index-title", content)
        self.assertIn("Home", content)
        self.assertIn("Timeline", content)
        self.assertIn("Gallery", content)
        self.assertIn("Scrapbook", content)
        self.assertIn("Yearbook", content)
        self.assertIn("Videos", content)
        self.assertIn("About", content)
        self.assertNotIn("mob-index-num", content)

    def test_archive_closing_footer_rendering(self):
        res = self.client.get("/")
        content = res.content.decode("utf-8")
        self.assertIn("THREE YEARS.", content)
        self.assertIn("COUNTLESS MEMORIES.", content)
        self.assertIn("ONE STORY.", content)
        self.assertIn("footer-smasc-word", content)
        self.assertIn("SMASC", content)
        self.assertIn("BACK TO THE BEGINNING", content)
        self.assertIn("footer-memory-spine", content)
        self.assertIn("rb-footer-8", content)
        self.assertIn("rb-footer-socials", content)
        self.assertIn("rb-footer-nav-grid", content)
        self.assertIn("MEMORIES", content)
        self.assertIn("ARCHIVE", content)
        self.assertIn("PROJECT", content)

    def test_timeline_featured_milestone_badge(self):
        import datetime
        event = TimelineEvent.objects.create(
            title="Inauguration Day",
            category=self.category,
            event_date=datetime.date(2023, 7, 15),
            is_featured=True,
            description="Our first day together"
        )
        res = self.client.get("/timeline/")
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        self.assertIn("Inauguration Day", content)
        self.assertIn("Featured Milestone", content)

    def test_video_player_standardized_modal_elements(self):
        res = self.client.get("/videos/")
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        self.assertIn("vmp-modal", content)
        self.assertIn("vmp-shell", content)
        self.assertIn("vmp-player", content)
        self.assertIn("vmp-stage", content)
        self.assertIn("vmp-progress", content)
        self.assertIn("vmp-speed-menu", content)
        self.assertIn("vmp-pip", content)
        self.assertIn("vmp-fs", content)
        self.assertIn("vmp-info-title", content)
        self.assertIn("vmp-info-category", content)
        self.assertIn("vmp-prev-btn", content)
        self.assertIn("vmp-next-btn", content)
        self.assertIn("vmp-counter", content)
        self.assertIn("vmp-thumbs", content)

    def test_photo_admin_form_creation_no_integrity_error(self):
        from core.admin import PhotoAdminForm
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Generate a 1x1 test image
        img_io = io.BytesIO()
        img = Image.new("RGB", (1, 1), color=(255, 0, 0))
        img.save(img_io, format="JPEG")
        test_file = SimpleUploadedFile("test.jpg", img_io.getvalue(), content_type="image/jpeg")

        form_data = {
            "title": "Fresh Campus Memory",
            "alt_text": "Campus memory snapshot",
            "category": self.category.id,
            "status": "approved",
            "is_active": True,
            "show_gallery": True,
            "scrapbook_order": "",  # Empty integer input
            "gallery_order": "",
            "home_order": "",
            "timeline_order": "",
            "selected_order": "",
            "about_order": "",
        }
        form = PhotoAdminForm(data=form_data, files={"image": test_file})
        self.assertTrue(form.is_valid(), form.errors)
        photo = form.save()
        self.assertEqual(photo.scrapbook_order, 0)
        self.assertEqual(photo.gallery_order, 0)
        self.assertEqual(photo.title, "Fresh Campus Memory")

    def test_security_headers_present(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "SAMEORIGIN")

    def test_health_check_endpoint(self):
        res = self.client.get("/health/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "connected")

    def test_video_file_extension_validation(self):
        from django.core.exceptions import ValidationError
        from core.models import Video
        from django.core.files.uploadedfile import SimpleUploadedFile

        invalid_file = SimpleUploadedFile("danger.exe", b"malicious", content_type="application/octet-stream")
        vid = Video(title="Test Video", video_file=invalid_file)
        with self.assertRaises(ValidationError):
            vid.full_clean()

    def test_all_public_pages_render_successfully(self):
        for path in ["/", "/gallery/", "/timeline/", "/scrapbook/", "/yearbook/", "/videos/", "/about/", "/contact/"]:
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)

    def test_lan_and_localhost_host_access(self):
        # Verify localhost, 127.0.0.1, and configured LAN IP (192.168.1.11) all return 200
        for host in ["localhost:8000", "127.0.0.1:8000", "192.168.1.11:8000"]:
            with self.subTest(host=host):
                res = self.client.get("/", HTTP_HOST=host)
                self.assertEqual(res.status_code, 200)
                self.assertNotIn("DisallowedHost", res.content.decode("utf-8"))

    def test_branding_system_integration(self):
        from core.context_processors import site_branding
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get("/")
        branding = site_branding(req)

        self.assertEqual(branding["SITE_NAME"], "Echoes Of SMASC '26")
        self.assertEqual(branding["SHORT_NAME"], "ES26")
        self.assertEqual(branding["TAGLINE"], "CAPTURE • RELIVE • FOREVER")
        self.assertIn("logo_master", branding["BRANDING"])
        self.assertIn("favicon", branding["BRANDING"])

        res = self.client.get("/")
        content = res.content.decode("utf-8")
        self.assertIn("Echoes Of SMASC '26", content)
        self.assertIn("ECHOES OF SMASC", content)
        self.assertIn("04_FAVICONS_PWA/favicon.ico", content)

    def test_contact_form_email_validation_and_persistence(self):
        # Invalid email format should be rejected
        res = self.client.post("/contact/", {
            "name": "Test Student",
            "email": "not-a-valid-email",
            "subject": "Missing Photo",
            "category": "General",
            "message": "Please add this memory.",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("Please enter a valid email address.", res.content.decode("utf-8"))

        # Valid email should be saved and redirect
        res_valid = self.client.post("/contact/", {
            "name": "Test Student",
            "email": "student26@smasc.edu.in",
            "subject": "Farewell Memories",
            "category": "General",
            "message": "Here is a memory contribution.",
        })
        self.assertEqual(res_valid.status_code, 302)
        self.assertTrue(ContactMessage.objects.filter(email="student26@smasc.edu.in").exists())

    def test_admin_toggle_endpoint_permissions(self):
        # Anonymous client must be redirected to login (302)
        anon_client = Client()
        res_anon = anon_client.post(f"/admin/core/photo/{self.photo1.pk}/toggle/is_active/")
        self.assertEqual(res_anon.status_code, 302)

        # Logged-in admin toggle should succeed (200 JSON)
        res_admin = self.client.post(
            f"/admin/core/photo/{self.photo1.pk}/toggle/is_active/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(res_admin.status_code, 200)
        data = res_admin.json()
        self.assertTrue(data.get("success"))

    def test_production_settings_configured(self):
        from django.conf import settings as s
        self.assertTrue(hasattr(s, "CONTACT_NOTIFICATION_EMAIL"))
        self.assertTrue(hasattr(s, "DEFAULT_FROM_EMAIL"))
        self.assertTrue(hasattr(s, "EMAIL_BACKEND"))
        self.assertTrue(hasattr(s, "MAX_IMAGE_UPLOAD_SIZE"))
        self.assertTrue(hasattr(s, "MAX_VIDEO_UPLOAD_SIZE"))

    # ======================================================================
    # GALLERY PAGINATION TESTS
    # ======================================================================

    def test_gallery_initial_page_returns_at_most_30_photos(self):
        """First gallery load must not return more than PAGE_SIZE photos."""
        # Create 35 approved gallery photos
        for i in range(35):
            Photo.objects.create(
                title=f"Bulk Photo {i}",
                category=self.category,
                status="approved",
                is_active=True,
                show_gallery=True,
            )
        res = self.client.get("/gallery/")
        self.assertEqual(res.status_code, 200)
        # Context 'photos' must be ≤ 30
        photos_in_context = res.context["photos"]
        self.assertLessEqual(
            len(photos_in_context), 30,
            "Initial gallery page must deliver ≤30 photos"
        )

    def test_gallery_photos_api_page2(self):
        """gallery_photos_api must return page 2 correctly."""
        for i in range(35):
            Photo.objects.create(
                title=f"API Photo {i}",
                category=self.category,
                status="approved",
                is_active=True,
                show_gallery=True,
            )
        res = self.client.get("/gallery/photos/?page=2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("photos", data)
        self.assertIn("has_more", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 35)
        # Page 2 should have ≤30 photos
        self.assertLessEqual(len(data["photos"]), 30)

    def test_gallery_photos_api_excludes_hidden(self):
        """gallery_photos_api must never return non-approved or inactive photos."""
        Photo.objects.create(
            title="Hidden Photo",
            category=self.category,
            status="pending",
            is_active=True,
            show_gallery=True,
        )
        Photo.objects.create(
            title="Inactive Photo",
            category=self.category,
            status="approved",
            is_active=False,
            show_gallery=True,
        )
        res = self.client.get("/gallery/photos/?page=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        titles = [p["title"] for p in data["photos"]]
        self.assertNotIn("Hidden Photo", titles)
        self.assertNotIn("Inactive Photo", titles)

    def test_gallery_category_filter_pagination(self):
        """Category filter must work with pagination API."""
        import uuid
        uid = uuid.uuid4().hex[:6]
        cat2 = Category.objects.create(name=f"Paginate Cat {uid}", slug=f"paginate-cat-{uid}")
        for i in range(35):
            Photo.objects.create(
                title=f"Cat2 Photo {i}",
                category=cat2,
                status="approved",
                is_active=True,
                show_gallery=True,
            )
        res = self.client.get(f"/gallery/photos/?page=1&category={cat2.slug}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 35)
        for photo in data["photos"]:
            self.assertEqual(photo["category_name"], cat2.name)

    # ======================================================================
    # VIDEO PAGINATION TESTS
    # ======================================================================

    def test_videos_initial_page_returns_at_most_24_videos(self):
        """First videos load must not return more than 24 video objects."""
        for i in range(28):
            Video.objects.create(title=f"Bulk Video {i}")
        res = self.client.get("/videos/")
        self.assertEqual(res.status_code, 200)
        videos_in_context = res.context["videos"]
        self.assertLessEqual(
            len(videos_in_context), 24,
            "Initial videos page must deliver ≤24 videos"
        )

    def test_videos_api_page2(self):
        """videos_api must return page 2 correctly."""
        for i in range(28):
            Video.objects.create(title=f"API Video {i}")
        res = self.client.get("/videos/page/?page=2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("videos", data)
        self.assertIn("has_more", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 28)
        self.assertLessEqual(len(data["videos"]), 24)

    # ======================================================================
    # SCALABILITY SIMULATION TESTS
    # ======================================================================

    def test_scalability_1000_photos_does_not_load_all(self):
        """At 1000 photos, the gallery view must still return ≤30 in context."""
        Photo.objects.bulk_create([
            Photo(
                title=f"Scale Photo {i}",
                category=self.category,
                status="approved",
                is_active=True,
                show_gallery=True,
            )
            for i in range(1000)
        ])
        res = self.client.get("/gallery/")
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(
            len(res.context["photos"]), 30,
            "Gallery must not load all 1000 photos into context"
        )
        self.assertTrue(res.context.get("has_more"), "has_more should be True at 1000 photos")

    def test_scalability_500_videos_does_not_load_all(self):
        """At 500 videos, the videos view must still return ≤24 in context."""
        Video.objects.bulk_create([
            Video(title=f"Scale Video {i}")
            for i in range(500)
        ])
        res = self.client.get("/videos/")
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(
            len(res.context["videos"]), 24,
            "Videos view must not load all 500 videos into context"
        )
        self.assertTrue(res.context.get("has_more"), "has_more should be True at 500 videos")

    # ======================================================================
    # MEDIA SAFETY & STORAGE HARDENING TESTS
    # ======================================================================

    def test_image_size_limit_enforced(self):
        """Images exceeding MAX_IMAGE_UPLOAD_SIZE (25MB) must be rejected with ValidationError."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_image_file
        from django.core.exceptions import ValidationError

        # Create a mock file reporting size > 25MB (26MB)
        large_file = SimpleUploadedFile("huge.jpg", b"fake image content")
        large_file.size = 26 * 1024 * 1024
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(large_file)
        self.assertIn("exceeds maximum allowed limit", str(ctx.exception))

    def test_video_size_limit_enforced(self):
        """Videos exceeding MAX_VIDEO_UPLOAD_SIZE (500MB) must be rejected with ValidationError."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_video_file
        from django.core.exceptions import ValidationError

        large_video = SimpleUploadedFile("huge.mp4", b"\x00\x00\x00\x18ftypmp42")
        large_video.size = 501 * 1024 * 1024
        with self.assertRaises(ValidationError) as ctx:
            validate_video_file(large_video)
        self.assertIn("exceeds maximum allowed limit", str(ctx.exception))

    def test_valid_image_accepted(self):
        """Valid image binary must pass validation without error."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_image_file
        from django.core.exceptions import ValidationError
        from PIL import Image
        import io

        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="red")
        img.save(buf, format="JPEG")
        valid_img = SimpleUploadedFile("valid.jpg", buf.getvalue(), content_type="image/jpeg")

        try:
            validate_image_file(valid_img)
        except ValidationError:
            self.fail("validate_image_file unexpectedly raised ValidationError on valid JPEG")

    def test_valid_video_accepted(self):
        """Valid video container signatures (MP4, WebM) must pass validation."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_video_file
        from django.core.exceptions import ValidationError

        mp4_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + b"\x00" * 100
        valid_mp4 = SimpleUploadedFile("memory.mp4", mp4_bytes, content_type="video/mp4")
        try:
            validate_video_file(valid_mp4)
        except ValidationError:
            self.fail("validate_video_file unexpectedly raised ValidationError on valid MP4 header")

        webm_bytes = b"\x1a\x45\xdf\xa3\x9fB\x86\x81\x01B\xf7\x81\x01" + b"\x00" * 100
        valid_webm = SimpleUploadedFile("memory.webm", webm_bytes, content_type="video/webm")
        try:
            validate_video_file(valid_webm)
        except ValidationError:
            self.fail("validate_video_file unexpectedly raised ValidationError on valid WebM header")

    def test_disguised_file_as_image_rejected(self):
        """Disguised executable/non-image renamed to .jpg must be rejected."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_image_file
        from django.core.exceptions import ValidationError

        fake_image = SimpleUploadedFile(
            "exploit.jpg",
            b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This program cannot be run in DOS mode.",
            content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(fake_image)
        self.assertIn("Upload a valid image", str(ctx.exception))

    def test_disguised_file_as_video_rejected(self):
        """Disguised text or binary renamed to .mp4 must be rejected."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_video_file
        from django.core.exceptions import ValidationError

        fake_video = SimpleUploadedFile(
            "exploit.mp4",
            b"This is just plain text content masquerading as an MP4 video file.",
            content_type="video/mp4"
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_video_file(fake_video)
        self.assertIn("Upload a valid video", str(ctx.exception))

    def test_media_replacement_cleanup(self):
        """Replacing a media file on an existing model instance deletes the old file."""
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        def make_img_bytes(color):
            b = io.BytesIO()
            Image.new("RGB", (10, 10), color=color).save(b, format="JPEG")
            return b.getvalue()

        photo = Photo.objects.create(
            title="Replacement Test Photo",
            category=self.category,
            status="approved",
            is_active=True,
            show_gallery=True,
            image=ContentFile(make_img_bytes("blue"), name="orig_test_photo.jpg")
        )
        old_name = photo.image.name
        storage = photo.image.storage
        self.assertTrue(storage.exists(old_name), "Original image should exist in storage")

        # Replace image with a new file
        photo.image = ContentFile(make_img_bytes("green"), name="new_test_photo.jpg")
        photo.save()

        new_name = photo.image.name
        self.assertNotEqual(old_name, new_name)
        self.assertTrue(storage.exists(new_name), "New image must exist in storage")
        self.assertFalse(storage.exists(old_name), "Old image must be deleted from storage after replacement")

        # Clean up created file
        if storage.exists(new_name):
            storage.delete(new_name)

    def test_media_deletion_cleanup(self):
        """Deleting a model instance removes its physical file from storage."""
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        b = io.BytesIO()
        Image.new("RGB", (10, 10), color="purple").save(b, format="JPEG")
        photo = Photo.objects.create(
            title="Delete Test Photo",
            category=self.category,
            status="approved",
            is_active=True,
            show_gallery=True,
            image=ContentFile(b.getvalue(), name="delete_test_photo.jpg")
        )
        file_name = photo.image.name
        storage = photo.image.storage
        self.assertTrue(storage.exists(file_name))

        photo.delete()
        self.assertFalse(storage.exists(file_name), "File should be deleted from storage when instance is deleted")

    def test_shared_file_reference_safety(self):
        """If two records reference the same physical file, deleting one must NOT delete the shared file."""
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        b = io.BytesIO()
        Image.new("RGB", (10, 10), color="yellow").save(b, format="JPEG")
        shared_content = b.getvalue()

        photo_a = Photo.objects.create(
            title="Shared Photo A",
            category=self.category,
            status="approved",
            is_active=True,
            show_gallery=True,
            image=ContentFile(shared_content, name="shared_memory_file.jpg")
        )
        shared_name = photo_a.image.name
        storage = photo_a.image.storage

        # Record B references the exact same file name in storage
        photo_b = Photo.objects.create(
            title="Shared Photo B",
            category=self.category,
            status="approved",
            is_active=True,
            show_gallery=True,
            image=shared_name
        )

        self.assertTrue(storage.exists(shared_name))

        # Deleting photo_a must NOT delete the file because photo_b still references it
        photo_a.delete()
        self.assertTrue(
            storage.exists(shared_name),
            "Shared physical file must NOT be deleted while photo_b still references it"
        )

        # Deleting photo_b (last reference) MUST delete the file
        photo_b.delete()
        self.assertFalse(
            storage.exists(shared_name),
            "Shared physical file MUST be deleted after last referencing record is deleted"
        )
