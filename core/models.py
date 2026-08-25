import os
import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .validators import (
    validate_image_file,
    validate_video_file,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CATEGORY
# ============================================================================


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


# ============================================================================
# PHOTO / MAIN GALLERY
# ============================================================================


class Photo(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    title = models.CharField(
        max_length=200,
    )

    caption = models.TextField(
        blank=True,
    )

    alt_text = models.CharField(
        max_length=255,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
    )

    image = models.ImageField(
        upload_to="gallery/",
        validators=[validate_image_file],
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_photos",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="approved",
    )

    event_date = models.DateField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------------
    # FEATURED
    # ------------------------------------------------------------------------
    #
    # Used by the existing featured-memory system.
    #

    is_featured = models.BooleanField(
        default=False,
        verbose_name="Featured",
        help_text="Display this photograph as a featured memory.",
    )

    # ------------------------------------------------------------------------
    # MEMORY ATLAS
    # ------------------------------------------------------------------------
    #
    # NEW:
    # Allows the administrator to explicitly decide which images are used
    # inside the stacked Memory Atlas portal cover.
    #
    # This does NOT remove the photo from the normal Gallery.
    #

    show_in_atlas = models.BooleanField(
        default=False,
        verbose_name="Memory Atlas",
        help_text=(
            "Use this photograph as one of the cover photographs "
            "for its Memory Atlas category portal."
        ),
    )

    # ------------------------------------------------------------------------
    # MASTER STATE & VISIBILITY TOGGLES
    # ------------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Master active status for this photograph.",
    )

    show_gallery = models.BooleanField(
        default=True,
        verbose_name="Gallery",
        help_text="Display in Main Gallery.",
    )

    show_home = models.BooleanField(
        default=False,
        verbose_name="Home",
        help_text="Display on Home Page.",
    )

    show_timeline = models.BooleanField(
        default=False,
        verbose_name="Timeline",
        help_text="Display on Timeline.",
    )

    show_scrapbook = models.BooleanField(
        default=False,
        verbose_name="Scrapbook",
        help_text="Display in Scrapbook.",
    )

    show_selected_memories = models.BooleanField(
        default=False,
        verbose_name="Selected Memories",
        help_text="Display in Selected Memories.",
    )

    show_about = models.BooleanField(
        default=False,
        verbose_name="About",
        help_text="Display on About Page.",
    )

    # ------------------------------------------------------------------------
    # ORDERING FIELDS
    # ------------------------------------------------------------------------

    gallery_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Gallery Order",
    )

    home_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Home Order",
    )

    timeline_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Timeline Order",
    )

    scrapbook_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Scrapbook Order",
    )

    selected_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Selected Order",
    )

    about_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="About Order",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_active", "show_gallery"], name="photo_pub_gallery_idx"),
            models.Index(fields=["status", "is_active", "show_in_atlas"], name="photo_pub_atlas_idx"),
            models.Index(fields=["status", "is_active", "is_featured"], name="photo_pub_feat_idx"),
            models.Index(fields=["status", "is_active", "home_order", "-created_at"], name="photo_home_ord_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        """
        Model-level safety for Memory Atlas.

        Admin performs the friendly UI validation, but keeping the important
        rules here also protects database integrity when Photo objects are
        created from scripts, shell commands, imports, etc.
        """

        super().clean()

        if self.show_in_atlas:
            if self.status != "approved":
                raise ValidationError(
                    {
                        "show_in_atlas": (
                            "Only approved photographs can be used "
                            "inside Memory Atlas."
                        )
                    }
                )

            if not self.category:
                raise ValidationError(
                    {
                        "show_in_atlas": (
                            "Assign a category before adding this photograph "
                            "to Memory Atlas."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if self.gallery_order is None:
            self.gallery_order = 0
        if self.home_order is None:
            self.home_order = 0
        if self.timeline_order is None:
            self.timeline_order = 0
        if self.scrapbook_order is None:
            self.scrapbook_order = 0
        if self.selected_order is None:
            self.selected_order = 0
        if self.about_order is None:
            self.about_order = 0

        super().save(*args, **kwargs)


# ============================================================================
# TIMELINE
# ============================================================================


class TimelineEvent(models.Model):
    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    image = models.ImageField(
        upload_to="timeline/",
        blank=True,
        null=True,
        validators=[validate_image_file],
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events",
    )

    event_date = models.DateField()

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "event_date",
        ]
        indexes = [
            models.Index(fields=["is_featured", "display_order", "event_date"], name="tle_feat_ord_idx"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk and not self.display_order:
            max_order = (
                TimelineEvent.objects
                .aggregate(
                    models.Max("display_order")
                )
                .get("display_order__max")
            )

            self.display_order = (
                max_order or 0
            ) + 1

        super().save(*args, **kwargs)


# ============================================================================
# LEGACY / STANDALONE SCRAPBOOK ITEM
# ============================================================================


class ScrapbookItem(models.Model):
    title = models.CharField(
        max_length=200,
    )

    caption = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="scrapbook/",
        validators=[validate_image_file],
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrapbook_items",
    )

    rotation = models.IntegerField(
        default=0,
        help_text="Rotation in degrees. Example: -3, 0, 4",
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "-created_at",
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk and not self.display_order:
            max_order = (
                ScrapbookItem.objects
                .aggregate(
                    models.Max("display_order")
                )
                .get("display_order__max")
            )

            self.display_order = (
                max_order or 0
            ) + 1

        super().save(*args, **kwargs)


# ============================================================================
# YEARBOOK STUDENT
# ============================================================================


class Student(models.Model):
    name = models.CharField(
        max_length=150,
    )

    nickname = models.CharField(
        max_length=100,
        blank=True,
    )

    role = models.CharField(
        max_length=120,
        blank=True,
    )

    quote = models.CharField(
        max_length=255,
        blank=True,
    )

    bio = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="yearbook/",
        validators=[validate_image_file],
    )

    instagram_url = models.URLField(
        blank=True,
    )

    linkedin_url = models.URLField(
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "name",
        ]
        indexes = [
            models.Index(fields=["is_featured", "display_order", "name"], name="stu_feat_ord_idx"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk and not self.display_order:
            max_order = (
                Student.objects
                .aggregate(
                    models.Max("display_order")
                )
                .get("display_order__max")
            )

            self.display_order = (
                max_order or 0
            ) + 1

        super().save(*args, **kwargs)


# ============================================================================
# VIDEO
# ============================================================================


class Video(models.Model):
    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    video_file = models.FileField(
        upload_to="videos/",
        validators=[validate_video_file],
    )

    thumbnail = models.ImageField(
        upload_to="video_thumbnails/",
        blank=True,
        null=True,
        validators=[validate_image_file],
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="videos",
    )

    duration = models.CharField(
        max_length=20,
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "-created_at",
        ]
        indexes = [
            models.Index(fields=["is_featured", "display_order", "-created_at"], name="vid_feat_ord_idx"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk and not self.display_order:
            max_order = (
                Video.objects
                .aggregate(
                    models.Max("display_order")
                )
                .get("display_order__max")
            )

            self.display_order = (
                max_order or 0
            ) + 1

        super().save(*args, **kwargs)


# ============================================================================
# HERO SLIDES
# ============================================================================


class HeroSlide(models.Model):
    title = models.CharField(
        max_length=200,
        blank=True,
    )

    subtitle = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="hero/",
        validators=[validate_image_file],
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "created_at",
        ]
        indexes = [
            models.Index(fields=["is_active", "display_order", "created_at"], name="hs_act_ord_idx"),
        ]

    def __str__(self):
        if self.title:
            return self.title

        return f"Hero Slide {self.id}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.display_order:
            max_order = (
                HeroSlide.objects
                .aggregate(
                    models.Max("display_order")
                )
                .get("display_order__max")
            )

            self.display_order = (
                max_order or 0
            ) + 1

        super().save(*args, **kwargs)


# ============================================================================
# ABOUT PAGE
# ============================================================================


class AboutPage(models.Model):
    story_badge = models.CharField(
        max_length=100,
        default="THE ARCHIVE STORY",
    )

    story_title = models.CharField(
        max_length=200,
        default="Three Years. Countless Memories. One Story.",
    )

    story_paragraph_1 = models.TextField(
        default=(
            "Echoes Of SMASC '26 is a digital archive created to preserve "
            "the people, journeys, celebrations and everyday moments that "
            "defined our three years of college life."
        )
    )

    story_paragraph_2 = models.TextField(
        default=(
            "It is more than a gallery of photographs. It is a collection "
            "of friendships, laughter, lessons and memories that will "
            "continue to stay with us long after graduation."
        )
    )

    story_paragraph_3 = models.TextField(
        default=(
            "Built as a lightweight and permanent digital archive, this "
            "platform allows every member of our batch to revisit our "
            "journey anytime and anywhere."
        )
    )

    story_image = models.ImageField(
        upload_to="about/",
        blank=True,
        null=True,
        validators=[validate_image_file],
    )

    story_image_alt = models.CharField(
        max_length=255,
        default="BCA Class of 2026 final group photo",
    )

    background_photos = models.ManyToManyField(
        "Photo",
        blank=True,
        related_name="about_backgrounds",
        help_text=(
            "Select Gallery photos to display in the About page Drift Wall. "
            "If no photos are selected, the Drift Wall will remain empty."
        ),
    )

    class_info_title = models.CharField(
        max_length=100,
        default="Class Information",
    )

    class_info_text = models.TextField(
        default=(
            "Bachelor of Computer Applications (BCA)\n"
            "Class of 2026\n"
            "Three years of friendship and memories"
        )
    )

    archive_title = models.CharField(
        max_length=100,
        default="The Archive",
    )

    archive_text = models.TextField(
        default=(
            "A photography gallery, video collection, timeline, "
            "digital scrapbook and student yearbook."
        )
    )

    accessibility_title = models.CharField(
        max_length=100,
        default="Accessible Anywhere",
    )

    accessibility_text = models.TextField(
        default=(
            "Designed to remain fast, responsive and accessible "
            "across mobile phones, tablets, laptops and desktops."
        )
    )

    creator_name = models.CharField(
        max_length=100,
        default="Manoj Kumar S",
    )

    creator_role = models.CharField(
        max_length=100,
        default="Lead Developer & Creator",
    )

    creator_description = models.TextField(
        default=(
            "Designed and developed for the BCA Class of 2026 "
            "to preserve our college memories in a clean, responsive "
            "and lasting digital archive."
        )
    )

    creator_image = models.ImageField(
        upload_to="about/",
        blank=True,
        null=True,
        validators=[validate_image_file],
    )

    creator_image_alt = models.CharField(
        max_length=255,
        default="Manoj Kumar S",
    )

    created_for_text = models.CharField(
        max_length=150,
        default="Created for: BCA Class of 2026",
    )

    thanks_badge = models.CharField(
        max_length=100,
        default="GRATITUDE & ACKNOWLEDGEMENT",
    )

    thanks_title = models.CharField(
        max_length=100,
        default="Special Thanks",
    )

    thanks_text = models.TextField(
        default=(
            "We extend our heartfelt gratitude to our HOD, faculty members, "
            "class coordinators, mentors and every classmate who contributed "
            "photographs, videos, captions and memories to this archive."
        )
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "About Page Settings"
        verbose_name_plural = "About Page Settings"

    def __str__(self):
        return "About Page Configuration"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
        )

        return obj


# ============================================================================
# CONTACT PAGE SETTINGS
# ============================================================================


class ContactPage(models.Model):
    intro_badge = models.CharField(
        max_length=100,
        default="GET IN TOUCH",
    )

    intro_title = models.CharField(
        max_length=200,
        default="Let’s Keep the Memories Connected.",
    )

    intro_description = models.TextField(
        default=(
            "For feedback, missing memories, corrections, photo submissions, "
            "or archive-related queries, get in touch with us."
        )
    )

    email = models.EmailField(
        max_length=254,
        blank=True,
        default="contact@collegememories26.com",
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    location = models.CharField(
        max_length=200,
        blank=True,
        default="BCA Department, Class of 2026",
    )

    social_label_1 = models.CharField(
        max_length=100,
        blank=True,
        default="Instagram",
    )

    social_url_1 = models.URLField(
        blank=True,
        default="",
    )

    social_label_2 = models.CharField(
        max_length=100,
        blank=True,
        default="GitHub",
    )

    social_url_2 = models.URLField(
        blank=True,
        default="",
    )

    success_message = models.TextField(
        default=(
            "Thank you for reaching out! "
            "Your message has been sent successfully."
        )
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Contact Page Settings"
        verbose_name_plural = "Contact Page Settings"

    def __str__(self):
        return "Contact Page Configuration"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
        )

        return obj


# ============================================================================
# CONTACT MESSAGE
# ============================================================================


class ContactMessage(models.Model):
    CATEGORY_CHOICES = [
        (
            "General",
            "General Enquiry",
        ),
        (
            "Photo / Memory Submission",
            "Photo / Memory Submission",
        ),
        (
            "Correction",
            "Correction / Update",
        ),
        (
            "Technical Issue",
            "Technical Issue",
        ),
        (
            "Other",
            "Other",
        ),
    ]

    name = models.CharField(
        max_length=150,
    )

    email = models.EmailField(
        max_length=254,
    )

    subject = models.CharField(
        max_length=200,
    )

    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        default="General",
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return (
            f"{self.subject} — "
            f"{self.name} "
            f"({self.created_at.strftime('%Y-%m-%d')})"
        )


# ============================================================================
# SELECTED GALLERY PHOTO
# ============================================================================


class SelectedGalleryPhoto(models.Model):
    """
    Curated Selected Moments section.

    Maximum:
        10 ACTIVE photos.

    This is intentionally independent from:
        Photo.is_featured
        Photo.show_in_atlas
    """

    photo = models.OneToOneField(
        Photo,
        on_delete=models.CASCADE,
        related_name="selected_memory",
        limit_choices_to={
            "status": "approved",
        },
    )

    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order (1 to 10)",
    )

    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Enable or disable this photo "
            "in Selected Memories."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "order",
            "created_at",
        ]
        indexes = [
            models.Index(fields=["is_active", "order", "created_at"], name="sgp_act_ord_idx"),
        ]

        verbose_name = "Selected Memory"
        verbose_name_plural = "Selected Memories"

    def __str__(self):
        title = (
            self.photo.title
            if self.photo
            else "Photo"
        )

        return f"{self.order}. {title}"

    def clean(self):
        super().clean()

        if self.is_active:
            active_qs = (
                SelectedGalleryPhoto.objects
                .filter(is_active=True)
            )

            if self.pk:
                active_qs = active_qs.exclude(
                    pk=self.pk
                )

            if active_qs.count() >= 10:
                raise ValidationError(
                    "Selected Memories supports a maximum "
                    "of 10 active photos."
                )

        if (
            self.photo
            and self.photo.status != "approved"
        ):
            raise ValidationError(
                "Only approved gallery photos can be "
                "added to Selected Memories."
            )

        if self.is_active:
            if self.order < 1 or self.order > 10:
                raise ValidationError(
                    {
                        "order": (
                            "Selected Memory order must be "
                            "between 1 and 10."
                        )
                    }
                )

            duplicate_position = (
                SelectedGalleryPhoto.objects
                .filter(
                    is_active=True,
                    order=self.order,
                )
            )

            if self.pk:
                duplicate_position = (
                    duplicate_position.exclude(
                        pk=self.pk
                    )
                )

            if duplicate_position.exists():
                raise ValidationError(
                    {
                        "order": (
                            f"Selected Memory position "
                            f"{self.order} is already in use."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )


# ============================================================================
# SCRAPBOOK PLACEMENT
# ============================================================================


class ScrapbookPlacement(models.Model):
    SECTION_CHOICES = [
        (
            "pinned",
            "Pinned / Scratch Memories",
        ),
        (
            "film",
            "Moving Film Archive",
        ),
        (
            "mosaic",
            "Memory Mosaic",
        ),
        (
            "final",
            "Final Memory",
        ),
    ]

    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="scrapbook_placements",
        limit_choices_to={
            "status": "approved",
        },
    )

    section = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES,
        default="pinned",
    )

    custom_title = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Optional custom title override "
            "for this section."
        ),
    )

    custom_caption = models.TextField(
        blank=True,
        help_text=(
            "Optional custom caption override "
            "for this section."
        ),
    )

    rotation = models.IntegerField(
        default=0,
        help_text=(
            "Rotation angle in degrees "
            "(-3 to 3 recommended for "
            "Pinned Scratch Memories)."
        ),
    )

    FILM_STRIP_CHOICES = (
        (1, "Film Strip 1"),
        (2, "Film Strip 2"),
    )

    film_strip = models.PositiveSmallIntegerField(
        choices=FILM_STRIP_CHOICES,
        null=True,
        blank=True,
        help_text="Film strip selection (1 or 2). Only applicable for Moving Film Archive.",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order within this section.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Enable or disable this photo "
            "in the scrapbook section."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "section",
            "display_order",
            "-created_at",
        ]

        verbose_name = "Scrapbook Memory"
        verbose_name_plural = "Scrapbook Memories"

        indexes = [
            models.Index(fields=["section", "film_strip", "is_active"], name="sp_sec_strip_act_idx"),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["photo", "section", "film_strip"],
                condition=models.Q(section="film"),
                name="unique_film_photo_strip",
            ),
            models.UniqueConstraint(
                fields=["photo", "section"],
                condition=~models.Q(section="film"),
                name="unique_nonfilm_photo_section",
            ),
        ]

    def __str__(self):
        title = (
            self.photo.title
            if self.photo
            else "Photo"
        )

        return (
            f"[{self.get_section_display()}] "
            f"#{self.display_order} — "
            f"{title}"
        )

    def clean(self):
        super().clean()

        # -------------------------------------------------------------
        # MAX 8 PINNED SCRATCH MEMORIES
        # -------------------------------------------------------------
        if self.is_active and self.section == "pinned":
            pinned_qs = ScrapbookPlacement.objects.filter(
                section="pinned",
                is_active=True,
            )

            if self.pk:
                pinned_qs = pinned_qs.exclude(pk=self.pk)

            if pinned_qs.count() >= 8:
                raise ValidationError(
                    {
                        "section": (
                            "Maximum 8 active Pinned / Scratch Memories allowed."
                        )
                    }
                )

        # -------------------------------------------------------------
        # FILM STRIP VALIDATION & CAPACITY (MAX 10 PER STRIP)
        # -------------------------------------------------------------
        if self.section != "film":
            if self.film_strip is not None:
                raise ValidationError(
                    {
                        "film_strip": (
                            "Film Strip can only be assigned to Moving Film Archive memories."
                        )
                    }
                )
        else:
            if self.is_active and not self.film_strip:
                self.film_strip = 1

            if self.is_active and self.film_strip == 1:
                strip1_qs = ScrapbookPlacement.objects.filter(
                    section="film",
                    film_strip=1,
                    is_active=True,
                )
                if self.pk:
                    strip1_qs = strip1_qs.exclude(pk=self.pk)
                if strip1_qs.count() >= 10:
                    raise ValidationError(
                        {
                            "film_strip": (
                                "Film Strip 1 already contains 10 active photographs."
                            )
                        }
                    )

            if self.is_active and self.film_strip == 2:
                strip2_qs = ScrapbookPlacement.objects.filter(
                    section="film",
                    film_strip=2,
                    is_active=True,
                )
                if self.pk:
                    strip2_qs = strip2_qs.exclude(pk=self.pk)
                if strip2_qs.count() >= 10:
                    raise ValidationError(
                        {
                            "film_strip": (
                                "Film Strip 2 already contains 10 active photographs."
                            )
                        }
                    )

        # -------------------------------------------------------------
        # ONLY ONE FINAL MEMORY
        # -------------------------------------------------------------

        if (
            self.is_active
            and self.section == "final"
        ):
            final_qs = (
                ScrapbookPlacement.objects
                .filter(
                    section="final",
                    is_active=True,
                )
            )

            if self.pk:
                final_qs = final_qs.exclude(
                    pk=self.pk
                )

            # Auto-deactivate previous final memory placement if another exists

            if final_qs.exists():
                raise ValidationError(
                    "Only ONE active photograph is allowed "
                    "for 'Final Memory'."
                )

        # -------------------------------------------------------------
        # ONLY APPROVED GALLERY PHOTOS
        # -------------------------------------------------------------

        if (
            self.photo
            and self.photo.status != "approved"
        ):
            raise ValidationError(
                "Only approved gallery photos "
                "can be placed in Scrapbook."
            )

    def save(self, *args, **kwargs):
        if self.is_active and self.section == "final":
            ScrapbookPlacement.objects.filter(
                section="final",
                is_active=True,
            ).exclude(pk=self.pk if self.pk else None).update(is_active=False)

        if not self.pk and not self.display_order:
            max_order = (
                ScrapbookPlacement.objects
                .filter(section=self.section)
                .aggregate(
                    models.Max("display_order")
                )
                .get("display_order__max")
            )

            self.display_order = (
                max_order or 0
            ) + 1

        if not kwargs.get("update_fields"):
            self.full_clean()

        super().save(
            *args,
            **kwargs,
        )


# ============================================================================
# STORAGE-ABSTRACTED MEDIA LIFECYCLE & REFERENCE PROTECTION
# ============================================================================

MEDIA_MODEL_FIELDS = {
    Photo: ["image"],
    HeroSlide: ["image"],
    TimelineEvent: ["image"],
    Student: ["image"],
    Video: ["video_file", "thumbnail"],
    ScrapbookItem: ["image"],
    AboutPage: ["story_image", "creator_image"],
}


def is_file_referenced_elsewhere(file_name, excluding_instance=None):
    """
    Checks whether a file path/name is currently referenced anywhere else in the database.
    Prevents deleting shared files when one record is updated or deleted.
    """
    if not file_name:
        return False

    for model_cls, fields in MEDIA_MODEL_FIELDS.items():
        for field in fields:
            filter_kwargs = {field: file_name}
            qs = model_cls.objects.filter(**filter_kwargs)
            if excluding_instance and isinstance(excluding_instance, model_cls) and excluding_instance.pk:
                qs = qs.exclude(pk=excluding_instance.pk)
            if qs.exists():
                return True
    return False


def cleanup_storage_file_safely(field_file, excluding_instance=None):
    """
    Safely deletes a physical media file using Django's Storage abstraction
    if and only if no other database record references it.
    """
    if not field_file or not getattr(field_file, "name", None):
        return

    file_name = field_file.name
    try:
        storage = field_file.storage
    except Exception:
        return

    if not is_file_referenced_elsewhere(file_name, excluding_instance=excluding_instance):
        try:
            if storage.exists(file_name):
                storage.delete(file_name)
        except Exception as e:
            logger.warning("Could not delete unreferenced media file %s: %s", file_name, e)


@receiver(pre_save)
def track_replaced_files(sender, instance, **kwargs):
    """
    Before saving a modified instance, record any replaced media files so they
    can be cleaned up after the new record is successfully saved.
    """
    if sender not in MEDIA_MODEL_FIELDS or not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_files = []
    for field_name in MEDIA_MODEL_FIELDS[sender]:
        old_field = getattr(old_instance, field_name, None)
        new_field = getattr(instance, field_name, None)
        old_name = getattr(old_field, "name", None) if old_field else None
        new_name = getattr(new_field, "name", None) if new_field else None

        if old_name and old_name != new_name:
            old_files.append(old_field)

    instance._old_files_to_cleanup = old_files


@receiver(post_save)
def cleanup_replaced_files(sender, instance, **kwargs):
    """
    After a successful save, safely delete any replaced media files.
    """
    if sender not in MEDIA_MODEL_FIELDS:
        return

    old_files = getattr(instance, "_old_files_to_cleanup", None)
    if old_files:
        for old_file in old_files:
            cleanup_storage_file_safely(old_file, excluding_instance=instance)
        instance._old_files_to_cleanup = None


@receiver(post_delete)
def cleanup_deleted_files(sender, instance, **kwargs):
    """
    When an instance is deleted (individually or in bulk), safely clean up
    its physical media files if unreferenced elsewhere.
    """
    if sender not in MEDIA_MODEL_FIELDS:
        return

    for field_name in MEDIA_MODEL_FIELDS[sender]:
        field_file = getattr(instance, field_name, None)
        if field_file:
            cleanup_storage_file_safely(field_file, excluding_instance=instance)


@receiver(post_save)
@receiver(post_delete)
def invalidate_public_cache(sender, **kwargs):
    """
    Automatically invalidate public page caches when any CMS content is created, updated, or deleted.
    """
    from django.core.cache import cache
    cache_models = (
        Photo, Category, HeroSlide, TimelineEvent,
        ScrapbookItem, ScrapbookPlacement, Student,
        Video, AboutPage, ContactPage, SelectedGalleryPhoto
    )
    if sender in cache_models:
        try:
            cache.clear()
        except Exception:
            pass
