from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminDateWidget

from .models import (
    Category,
    Photo,
    SelectedGalleryPhoto,
    TimelineEvent,
    ScrapbookItem,
    ScrapbookPlacement,
    Student,
    Video,
    HeroSlide,
    AboutPage,
    ContactPage,
    ContactMessage,
)


# ============================================================================
# CUSTOM DATE WIDGET
# ============================================================================


class UnfoldAdminDateInputWidget(UnfoldAdminDateWidget):
    """
    HTML5 date input.

    Gives direct:
    - Year
    - Month
    - Day

    selection inside Django Admin.
    """

    input_type = "date"


# ============================================================================
# SHARED ADMIN MEDIA
# ============================================================================


ADMIN_IMAGE_PREVIEW_MEDIA = {
    "css": {
        "all": (
            "admin/css/image-preview.css",
        )
    },
    "js": (
        "admin/js/image-preview.js",
    ),
}


# ============================================================================
# ADMIN SITE BRANDING
# ============================================================================


admin.site.site_header = "Echoes Of SMASC '26"
admin.site.site_title = "Echoes Of SMASC '26"
admin.site.index_title = "Echoes Of SMASC '26 Administration"


# ============================================================================
# CATEGORY ADMIN
# ============================================================================


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "description",
    )

    search_fields = (
        "name",
        "slug",
        "description",
    )

    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }

    ordering = (
        "name",
    )

    list_per_page = 20


# ============================================================================
# PHOTO GALLERY FILTERS
# ============================================================================


class SelectedMemoryListFilter(admin.SimpleListFilter):
    """
    Quickly filter Photo records according to whether they are
    currently used inside Selected Memories.
    """

    title = "Selected Memory"
    parameter_name = "in_selected_memories"

    def lookups(self, request, model_admin):
        return (
            (
                "yes",
                "Selected",
            ),
            (
                "no",
                "Not Selected",
            ),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == "yes":
            return queryset.filter(
                selected_memory__is_active=True
            )

        if value == "no":
            return queryset.exclude(
                selected_memory__is_active=True
            )

        return queryset


class AtlasPhotoListFilter(admin.SimpleListFilter):
    """
    Quickly find photographs enabled as Memory Atlas covers.
    """

    title = "Memory Atlas"
    parameter_name = "in_memory_atlas"

    def lookups(self, request, model_admin):
        return (
            (
                "yes",
                "In Atlas",
            ),
            (
                "no",
                "Not In Atlas",
            ),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == "yes":
            return queryset.filter(
                show_in_atlas=True
            )

        if value == "no":
            return queryset.filter(
                show_in_atlas=False
            )

        return queryset


class ScrapbookPhotoListFilter(admin.SimpleListFilter):
    """
    Quickly filter Photo records according to whether they are
    currently used inside Scrapbook.
    """

    title = "Scrapbook"
    parameter_name = "in_scrapbook"

    def lookups(self, request, model_admin):
        return (
            (
                "yes",
                "In Scrapbook",
            ),
            (
                "no",
                "Not In Scrapbook",
            ),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == "yes":
            return queryset.filter(
                scrapbook_placements__is_active=True
            ).distinct()

        if value == "no":
            return queryset.exclude(
                scrapbook_placements__is_active=True
            )

        return queryset


# ============================================================================
# PHOTO ADMIN FORM
# ============================================================================


class PhotoAdminForm(forms.ModelForm):
    """
    Full Photo edit form.

    Photo selection architecture:

    Featured
        Controlled by Photo.is_featured.

    Memory Atlas
        Controlled by Photo.show_in_atlas.

    Selected Memory
        Controlled through SelectedGalleryPhoto.

    Scrapbook Placement
        Controlled through ScrapbookPlacement.
    """

    selected_memories = forms.BooleanField(
        required=False,
        label="Selected Memory",
        help_text=(
            "Display this photograph inside "
            "the curated Selected Moments section."
        ),
    )

    selected_memories_order = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        label="Selected Memory Position",
        help_text=(
            "Display position from 1 to 10. "
            "Leave empty to automatically use "
            "the first available position."
        ),
    )

    in_scrapbook = forms.BooleanField(
        required=False,
        label="Scrapbook Memory",
        help_text="Display this photograph on the public Scrapbook page.",
    )

    scrapbook_section = forms.ChoiceField(
        choices=[("", "-- Select Section --")] + ScrapbookPlacement.SECTION_CHOICES,
        required=False,
        label="Scrapbook Section",
        help_text="Choose section: Pinned / Scratch Memories, Moving Film Archive, Memory Mosaic, or Final Memory.",
    )

    scrapbook_rotation = forms.IntegerField(
        required=False,
        initial=0,
        label="Scrapbook Rotation (Degrees)",
        help_text="Rotation angle in degrees (-5 to 5 recommended).",
    )

    scrapbook_order = forms.IntegerField(
        required=False,
        initial=0,
        min_value=0,
        label="Scrapbook Display Order",
        help_text="Order within selected Scrapbook section.",
    )

    scrapbook_custom_title = forms.CharField(
        max_length=200,
        required=False,
        label="Scrapbook Custom Title",
        help_text="Optional custom title override for Scrapbook page.",
    )

    scrapbook_custom_caption = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Scrapbook Custom Caption",
        help_text="Optional custom caption override for Scrapbook page.",
    )

    class Meta:
        model = Photo
        fields = "__all__"

    # ------------------------------------------------------------------------
    # INITIAL VALUES
    # ------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
        )

        if (
            self.instance
            and self.instance.pk
        ):
            try:
                selected_item = (
                    SelectedGalleryPhoto.objects
                    .filter(
                        photo=self.instance,
                        is_active=True,
                    )
                    .first()
                )

                if selected_item:
                    self.fields[
                        "selected_memories"
                    ].initial = True

                    self.fields[
                        "selected_memories_order"
                    ].initial = selected_item.order

            except Exception:
                pass

            try:
                placement = (
                    ScrapbookPlacement.objects
                    .filter(
                        photo=self.instance,
                        is_active=True,
                    )
                    .first()
                )

                if placement:
                    self.fields["in_scrapbook"].initial = True
                    self.fields["scrapbook_section"].initial = placement.section
                    self.fields["scrapbook_rotation"].initial = placement.rotation
                    self.fields["scrapbook_order"].initial = placement.display_order
                    self.fields["scrapbook_custom_title"].initial = placement.custom_title
                    self.fields["scrapbook_custom_caption"].initial = placement.custom_caption
            except Exception:
                pass
        else:
            if "status" in self.fields:
                self.fields["status"].initial = "approved"
            if "is_active" in self.fields:
                self.fields["is_active"].initial = True
            if "show_gallery" in self.fields:
                self.fields["show_gallery"].initial = True

    # ------------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()

        status = cleaned_data.get(
            "status"
        )

        category = cleaned_data.get(
            "category"
        )

        show_in_atlas = cleaned_data.get(
            "show_in_atlas"
        )

        selected = cleaned_data.get(
            "selected_memories"
        )

        selected_order = cleaned_data.get(
            "selected_memories_order"
        )

        in_scrapbook = cleaned_data.get(
            "in_scrapbook"
        )

        scrapbook_section = cleaned_data.get(
            "scrapbook_section"
        )

        if in_scrapbook:
            if status != "approved":
                self.add_error(
                    "in_scrapbook",
                    "Only approved photographs can be placed in Scrapbook.",
                )

            if not scrapbook_section:
                self.add_error(
                    "scrapbook_section",
                    "Please select a section for Scrapbook placement.",
                )

            if scrapbook_section == "final":
                final_qs = ScrapbookPlacement.objects.filter(
                    section="final",
                    is_active=True,
                )
                if self.instance and self.instance.pk:
                    final_qs = final_qs.exclude(photo=self.instance)
                if final_qs.exists():
                    self.add_error(
                        "scrapbook_section",
                        "Only ONE photograph can be set as 'Final Memory'. Another photo is already active.",
                    )

        # ================================================================
        # MEMORY ATLAS
        # ================================================================

        if show_in_atlas:
            if status != "approved":
                self.add_error(
                    "show_in_atlas",
                    (
                        "Approve this photograph before "
                        "adding it to Memory Atlas."
                    ),
                )

            if not category:
                self.add_error(
                    "show_in_atlas",
                    (
                        "Assign a category before "
                        "adding this photograph to Memory Atlas."
                    ),
                )

            if category:
                atlas_qs = Photo.objects.filter(
                    category=category,
                    status="approved",
                    show_in_atlas=True,
                )

                if (
                    self.instance
                    and self.instance.pk
                ):
                    atlas_qs = atlas_qs.exclude(
                        pk=self.instance.pk
                    )

                if atlas_qs.count() >= 4:
                    self.add_error(
                        "show_in_atlas",
                        (
                            f'"{category.name}" already contains '
                            "four Memory Atlas cover photographs. "
                            "Remove one before selecting another."
                        ),
                    )

        # ================================================================
        # SELECTED MEMORIES
        # ================================================================

        if selected:
            if status != "approved":
                self.add_error(
                    "selected_memories",
                    (
                        "Only approved photographs can be "
                        "added to Selected Memories."
                    ),
                )

                return cleaned_data

            active_qs = (
                SelectedGalleryPhoto.objects
                .filter(
                    is_active=True
                )
            )

            if (
                self.instance
                and self.instance.pk
            ):
                active_qs = active_qs.exclude(
                    photo=self.instance
                )

            if active_qs.count() >= 10:
                self.add_error(
                    "selected_memories",
                    (
                        "Selected Memories already contains "
                        "10 active photographs. "
                        "Remove one before adding another."
                    ),
                )

                return cleaned_data

            # ------------------------------------------------------------
            # Manual order
            # ------------------------------------------------------------

            if selected_order is not None:
                used_order_qs = (
                    SelectedGalleryPhoto.objects
                    .filter(
                        is_active=True,
                        order=selected_order,
                    )
                )

                if (
                    self.instance
                    and self.instance.pk
                ):
                    used_order_qs = (
                        used_order_qs.exclude(
                            photo=self.instance
                        )
                    )

                if used_order_qs.exists():
                    self.add_error(
                        "selected_memories_order",
                        (
                            f"Selected Memories position "
                            f"{selected_order} is already being used."
                        ),
                    )

            # ------------------------------------------------------------
            # Automatic order
            # ------------------------------------------------------------

            else:
                used_orders = set(
                    active_qs.values_list(
                        "order",
                        flat=True,
                    )
                )

                available_orders = [
                    number
                    for number in range(
                        1,
                        11,
                    )
                    if number not in used_orders
                ]

                if available_orders:
                    cleaned_data[
                        "selected_memories_order"
                    ] = available_orders[0]

                else:
                    self.add_error(
                        "selected_memories_order",
                        (
                            "All Selected Memories positions "
                            "from 1 to 10 are currently occupied."
                        ),
                    )
        # Ensure integer fields are never None
        for int_field in (
            "scrapbook_order",
            "scrapbook_rotation",
            "gallery_order",
            "home_order",
            "timeline_order",
            "selected_order",
            "about_order",
        ):
            if int_field in cleaned_data and cleaned_data[int_field] is None:
                cleaned_data[int_field] = 0

        return cleaned_data


# ============================================================================
# PHOTO GALLERY ADMIN
# ============================================================================


@admin.register(Photo)
class PhotoAdmin(ModelAdmin):
    """
    MAIN USER-FRIENDLY PHOTO MANAGEMENT SCREEN.

    Admin list controls:

        FEATURED
        ATLAS
        SELECTED

    All three are independent.
    """

    form = PhotoAdminForm

    # ------------------------------------------------------------------------
    # MEDIA
    # ------------------------------------------------------------------------

    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    # ------------------------------------------------------------------------
    # DATE INPUT
    # ------------------------------------------------------------------------

    formfield_overrides = {
        models.DateField: {
            "widget": UnfoldAdminDateInputWidget,
        },
    }

    # ------------------------------------------------------------------------
    # TABLE
    # ------------------------------------------------------------------------

    list_display = (
        "id",
        "thumbnail_preview",
        "title",
        "category",
        "status",
        "toggle_is_active",
        "toggle_is_featured",
        "toggle_show_atlas",
        "toggle_selected",
        "toggle_scrapbook",
        "toggle_fragments",
        "toggle_film_strip_1",
        "toggle_film_strip_2",
        "uploaded_by",
        "created_at",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "title",
    )

    # Keep Status directly editable.
    #
    # Featured / Atlas / Selected are deliberately buttons,
    # so there is no Save button required after toggling.

    list_editable = (
        "status",
    )

    list_filter = (
        "status",
        "is_featured",
        AtlasPhotoListFilter,
        SelectedMemoryListFilter,
        ScrapbookPhotoListFilter,
        "category",
        "created_at",
    )

    search_fields = (
        "title",
        "caption",
        "alt_text",
        "category__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "where_used_panel",
    )

    list_select_related = (
        "category",
        "uploaded_by",
        "selected_memory",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 20

    date_hierarchy = "created_at"

    @admin.display(description="Active Placements")
    def where_used_panel(self, obj):
        if not obj or not obj.pk:
            return "Save the photo first to view live placement details."

        placements_info = []

        # Gallery
        if obj.is_active and obj.status == "approved" and obj.show_gallery:
            placements_info.append(f'<li style="margin-bottom:6px;"><strong style="color:#10B981;">✓ Gallery:</strong> Active (Order #{obj.gallery_order})</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ Gallery: Inactive</li>')

        # Memory Atlas
        if obj.show_in_atlas:
            placements_info.append('<li style="margin-bottom:6px;"><strong style="color:#10B981;">✓ Memory Atlas:</strong> Active Cover</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ Memory Atlas: Inactive</li>')

        # Selected Memories
        sel = SelectedGalleryPhoto.objects.filter(photo=obj, is_active=True).first()
        if sel:
            placements_info.append(f'<li style="margin-bottom:6px;"><strong style="color:#10B981;">✓ Selected Memories:</strong> Active (Position #{sel.order})</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ Selected Memories: Inactive</li>')

        # Scrapbook
        sp = ScrapbookPlacement.objects.filter(photo=obj, is_active=True).first()
        if sp:
            placements_info.append(f'<li style="margin-bottom:6px;"><strong style="color:#D7B377;">✓ Scrapbook:</strong> Active ({sp.get_section_display()} — Order #{sp.display_order})</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ Scrapbook: Inactive</li>')

        # Timeline
        if obj.show_timeline:
            placements_info.append(f'<li style="margin-bottom:6px;"><strong style="color:#10B981;">✓ Timeline:</strong> Active (Order #{obj.timeline_order})</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ Timeline: Inactive</li>')

        # Home
        if obj.show_home:
            placements_info.append(f'<li style="margin-bottom:6px;"><strong style="color:#10B981;">✓ Home Page:</strong> Active (Order #{obj.home_order})</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ Home Page: Inactive</li>')

        # About
        if obj.show_about:
            placements_info.append(f'<li style="margin-bottom:6px;"><strong style="color:#10B981;">✓ About Page:</strong> Active (Order #{obj.about_order})</li>')
        else:
            placements_info.append('<li style="margin-bottom:6px; color:#94A3B8;">✕ About Page: Inactive</li>')

        html = f"""
        <div style="background:rgba(15,15,15,0.7); border:1px solid rgba(215,179,119,0.3); border-radius:10px; padding:14px 18px;">
            <ul style="list-style:none; margin:0; padding:0; font-size:13px; line-height:1.6;">
                {''.join(placements_info)}
            </ul>
        </div>
        """
        return mark_safe(html)

    # ------------------------------------------------------------------------
    # EDIT PAGE
    # ------------------------------------------------------------------------

    fieldsets = (
        (
            "BASIC INFORMATION",
            {
                "fields": (
                    "image",
                    "title",
                    "caption",
                    "alt_text",
                    "category",
                    "event_date",
                ),
            },
        ),

        (
            "WHERE IS THIS PHOTO USED?",
            {
                "fields": (
                    "where_used_panel",
                ),
                "description": "Live status of where this photo is active across the platform.",
            },
        ),

        (
            "MASTER STATUS",
            {
                "fields": (
                    "is_active",
                    "status",
                    "uploaded_by",
                ),
            },
        ),

        (
            "DISPLAY ON WEBSITE",
            {
                "fields": (
                    "show_gallery",
                    "show_home",
                    "show_timeline",
                    "show_scrapbook",
                    "show_selected_memories",
                    "show_about",
                    "show_in_atlas",
                    "is_featured",
                ),
                "description": "Toggle master visibility per section.",
            },
        ),

        (
            "SCRAPBOOK CONFIGURATION",
            {
                "classes": ("scrapbook-config-fieldset",),
                "fields": (
                    "in_scrapbook",
                    "scrapbook_section",
                    "scrapbook_rotation",
                    "scrapbook_order",
                    "scrapbook_custom_title",
                    "scrapbook_custom_caption",
                ),
                "description": (
                    "Configure Scrapbook placement settings. "
                    "Max 8 Pinned / Scratch Memories allowed. "
                    "Only 1 Final Memory allowed globally."
                ),
            },
        ),

        (
            "SELECTED MEMORY CONFIGURATION",
            {
                "classes": ("selected-config-fieldset",),
                "fields": (
                    "selected_memories",
                    "selected_memories_order",
                ),
                "description": "Maximum 10 active Selected Memories allowed.",
            },
        ),

        (
            "ORDERING",
            {
                "fields": (
                    "gallery_order",
                    "home_order",
                    "timeline_order",
                    "about_order",
                ),
            },
        ),

        (
            "SYSTEM INFORMATION",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    # ------------------------------------------------------------------------
    # BULK ACTIONS
    # ------------------------------------------------------------------------

    actions = (
        "approve_selected",
        "reject_selected",
        "mark_featured",
        "remove_featured",
        "add_to_atlas",
        "remove_from_atlas",
    )

    # =========================================================================
    # QUERY OPTIMIZATION
    # =========================================================================

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "category",
                "uploaded_by",
            )
        )

    # =========================================================================
    # CUSTOM BUTTON URLS
    # =========================================================================

    def get_urls(self):
        normal_urls = super().get_urls()

        custom_urls = [
            path(
                "<path:object_id>/toggle/<str:field_name>/",
                self.admin_site.admin_view(
                    self.toggle_field_view
                ),
                name="core_photo_toggle_field",
            ),

            path(
                "<int:photo_id>/toggle-featured/",
                self.admin_site.admin_view(
                    self.toggle_featured_view
                ),
                name=(
                    "core_photo_toggle_featured"
                ),
            ),

            path(
                "<int:photo_id>/toggle-atlas/",
                self.admin_site.admin_view(
                    self.toggle_atlas_view
                ),
                name=(
                    "core_photo_toggle_atlas"
                ),
            ),

            path(
                "<int:photo_id>/toggle-selected-memory/",
                self.admin_site.admin_view(
                    self.toggle_selected_memory_view
                ),
                name=(
                    "core_photo_toggle_selected_memory"
                ),
            ),
        ]

        return (
            custom_urls
            + normal_urls
        )

    def toggle_field_view(self, request, object_id, field_name):
        from django.http import JsonResponse
        if request.method != "POST":
            return JsonResponse({"error": "POST request required"}, status=400)

        photo = self.get_object(request, object_id)
        if not photo:
            return JsonResponse({"error": "Photo not found"}, status=404)

        if not self.has_change_permission(request, photo):
            return JsonResponse({"error": "Permission denied"}, status=403)

        with transaction.atomic():
            if field_name == "is_active":
                photo.is_active = not photo.is_active
                photo.save(update_fields=["is_active"])
                new_state = photo.is_active
            elif field_name == "is_featured":
                photo.is_featured = not photo.is_featured
                photo.save(update_fields=["is_featured"])
                new_state = photo.is_featured
            elif field_name == "show_in_atlas":
                if not photo.show_in_atlas and photo.status != "approved":
                    return JsonResponse({"error": "Approve photo before enabling Atlas"}, status=400)
                photo.show_in_atlas = not photo.show_in_atlas
                photo.save(update_fields=["show_in_atlas"])
                new_state = photo.show_in_atlas
            elif field_name == "selected":
                sel = SelectedGalleryPhoto.objects.filter(photo=photo).first()
                if sel and sel.is_active:
                    sel.delete()
                    new_state = False
                else:
                    if photo.status != "approved":
                        return JsonResponse({"error": "Approve photo before adding to Selected"}, status=400)
                    active_cnt = SelectedGalleryPhoto.objects.filter(is_active=True).count()
                    if active_cnt >= 10:
                        return JsonResponse({"error": "Maximum 10 active Selected Memories allowed"}, status=400)
                    used_orders = set(SelectedGalleryPhoto.objects.filter(is_active=True).values_list("order", flat=True))
                    avail = [i for i in range(1, 11) if i not in used_orders]
                    order = avail[0] if avail else 1
                    SelectedGalleryPhoto.objects.update_or_create(photo=photo, defaults={"order": order, "is_active": True})
                    new_state = True
            elif field_name == "scrapbook":
                sp = ScrapbookPlacement.objects.filter(photo=photo, section="pinned").first()
                if sp and sp.is_active:
                    sp.is_active = False
                    sp.save(update_fields=["is_active"])
                    new_state = False
                else:
                    if photo.status != "approved":
                        return JsonResponse({"error": "Approve photo before adding to Scrapbook"}, status=400)
                    pinned_cnt = ScrapbookPlacement.objects.filter(section="pinned", is_active=True).count()
                    if pinned_cnt >= 8:
                        return JsonResponse({"error": "Maximum 8 active Pinned Memories allowed"}, status=400)
                    ScrapbookPlacement.objects.update_or_create(
                        photo=photo,
                        section="pinned",
                        defaults={"rotation": 0, "display_order": pinned_cnt + 1, "is_active": True}
                    )
                    new_state = True
            elif field_name in ("memory_fragments", "fragments", "mosaic"):
                sp = ScrapbookPlacement.objects.filter(photo=photo, section="mosaic").first()
                if sp and sp.is_active:
                    sp.is_active = False
                    sp.save(update_fields=["is_active"])
                    new_state = False
                else:
                    if photo.status != "approved":
                        return JsonResponse({"error": "Approve photo before adding to Memory Fragments"}, status=400)
                    if not photo.is_active:
                        return JsonResponse({"error": "Activate photo before adding to Memory Fragments"}, status=400)
                    max_order = ScrapbookPlacement.objects.filter(section="mosaic", is_active=True).aggregate(models.Max("display_order"))["display_order__max"] or 0
                    ScrapbookPlacement.objects.update_or_create(
                        photo=photo,
                        section="mosaic",
                        defaults={"is_active": True, "display_order": max_order + 1 if not sp else sp.display_order}
                    )
                    new_state = True
            elif field_name in ("film_strip_1", "film1", "strip1"):
                sp = ScrapbookPlacement.objects.filter(photo=photo, section="film", film_strip=1).first()
                if sp and sp.is_active:
                    sp.is_active = False
                    sp.save(update_fields=["is_active"])
                    new_state = False
                else:
                    if photo.status != "approved":
                        return JsonResponse({"error": "Approve photo before adding to Film Strip 1"}, status=400)
                    if not photo.is_active:
                        return JsonResponse({"error": "Activate photo before adding to Film Strip 1"}, status=400)
                    cnt = ScrapbookPlacement.objects.filter(section="film", film_strip=1, is_active=True).exclude(photo=photo).count()
                    if cnt >= 10:
                        return JsonResponse({"error": "Film Strip 1 already contains 10 active photographs."}, status=400)
                    max_order = ScrapbookPlacement.objects.filter(section="film", film_strip=1, is_active=True).aggregate(models.Max("display_order"))["display_order__max"] or 0
                    ScrapbookPlacement.objects.update_or_create(
                        photo=photo,
                        section="film",
                        film_strip=1,
                        defaults={"is_active": True, "display_order": max_order + 1 if not sp else sp.display_order}
                    )
                    new_state = True
            elif field_name in ("film_strip_2", "film2", "strip2"):
                sp = ScrapbookPlacement.objects.filter(photo=photo, section="film", film_strip=2).first()
                if sp and sp.is_active:
                    sp.is_active = False
                    sp.save(update_fields=["is_active"])
                    new_state = False
                else:
                    if photo.status != "approved":
                        return JsonResponse({"error": "Approve photo before adding to Film Strip 2"}, status=400)
                    if not photo.is_active:
                        return JsonResponse({"error": "Activate photo before adding to Film Strip 2"}, status=400)
                    cnt = ScrapbookPlacement.objects.filter(section="film", film_strip=2, is_active=True).exclude(photo=photo).count()
                    if cnt >= 10:
                        return JsonResponse({"error": "Film Strip 2 already contains 10 active photographs."}, status=400)
                    max_order = ScrapbookPlacement.objects.filter(section="film", film_strip=2, is_active=True).aggregate(models.Max("display_order"))["display_order__max"] or 0
                    ScrapbookPlacement.objects.update_or_create(
                        photo=photo,
                        section="film",
                        film_strip=2,
                        defaults={"is_active": True, "display_order": max_order + 1 if not sp else sp.display_order}
                    )
                    new_state = True
            else:
                return JsonResponse({"error": "Invalid field"}, status=400)

        return JsonResponse({"success": True, "new_state": new_state})

    # =========================================================================
    # REDIRECT HELPER
    # =========================================================================

    def _return_to_photo_list(
        self,
        request,
    ):
        """
        Return the administrator to the same changelist/filter page.
        """

        return redirect(
            request.META.get(
                "HTTP_REFERER"
            )
            or reverse(
                "admin:core_photo_changelist"
            )
        )

    # =========================================================================
    # BUTTON STYLE
    # =========================================================================

    def _toggle_button(
        self,
        *,
        url,
        enabled,
        enabled_label,
        disabled_label,
        enabled_color="#16A34A",
        enabled_border="#22C55E",
    ):
        if enabled:
            return format_html(
                """
                <a
                    href="{}"
                    title="Click to disable"
                    style="
                        display:inline-flex;
                        align-items:center;
                        justify-content:center;
                        gap:5px;
                        min-width:82px;
                        height:32px;
                        padding:0 12px;
                        border-radius:999px;
                        border:1px solid {};
                        background:{};
                        color:#FFFFFF;
                        font-size:11px;
                        font-weight:800;
                        letter-spacing:.045em;
                        text-decoration:none;
                        box-sizing:border-box;
                        box-shadow:0 5px 14px rgba(0,0,0,.14);
                        white-space:nowrap;
                    "
                >
                    ✓ {}
                </a>
                """,
                url,
                enabled_border,
                enabled_color,
                enabled_label,
            )

        return format_html(
            """
            <a
                href="{}"
                title="Click to enable"
                style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    gap:5px;
                    min-width:82px;
                    height:32px;
                    padding:0 12px;
                    border-radius:999px;
                    border:1px solid rgba(148,163,184,.30);
                    background:rgba(148,163,184,.07);
                    color:#94A3B8;
                    font-size:11px;
                    font-weight:800;
                    letter-spacing:.045em;
                    text-decoration:none;
                    box-sizing:border-box;
                    white-space:nowrap;
                "
            >
                + {}
            </a>
            """,
            url,
            disabled_label,
        )

    # =========================================================================
    # FEATURED BUTTON
    # =========================================================================

    @admin.display(
        description="Featured"
    )
    def featured_button(
        self,
        obj,
    ):
        url = reverse(
            "admin:core_photo_toggle_featured",
            args=[
                obj.pk,
            ],
        )

        return self._toggle_button(
            url=url,
            enabled=obj.is_featured,
            enabled_label="FEATURED",
            disabled_label="FEATURE",
        )

    # =========================================================================
    # ATLAS BUTTON
    # =========================================================================

    @admin.display(
        description="Memory Atlas"
    )
    def atlas_button(
        self,
        obj,
    ):
        url = reverse(
            "admin:core_photo_toggle_atlas",
            args=[
                obj.pk,
            ],
        )

        return self._toggle_button(
            url=url,
            enabled=obj.show_in_atlas,
            enabled_label="ATLAS",
            disabled_label="ATLAS",
            enabled_color="#B7791F",
            enabled_border="#D7B377",
        )

    # =========================================================================
    # SELECTED MEMORY BUTTON
    # =========================================================================

    @admin.display(
        description="Selected Memory"
    )
    def selected_memory_button(
        self,
        obj,
    ):
        selected_relation = None

        try:
            selected_relation = getattr(
                obj,
                "selected_memory",
                None,
            )

        except Exception:
            selected_relation = None

        selected = bool(
            selected_relation
            and selected_relation.is_active
        )

        url = reverse(
            "admin:core_photo_toggle_selected_memory",
            args=[
                obj.pk,
            ],
        )

        if selected:
            return format_html(
                """
                <a
                    href="{}"
                    title="Click to remove from Selected Memories"
                    style="
                        display:inline-flex;
                        align-items:center;
                        justify-content:center;
                        gap:5px;
                        min-width:106px;
                        height:32px;
                        padding:0 12px;
                        border-radius:999px;
                        border:1px solid #60A5FA;
                        background:#2563EB;
                        color:#FFFFFF;
                        font-size:11px;
                        font-weight:800;
                        letter-spacing:.035em;
                        text-decoration:none;
                        box-sizing:border-box;
                        box-shadow:0 5px 14px rgba(37,99,235,.18);
                        white-space:nowrap;
                    "
                >
                    ✓ SELECTED #{}
                </a>
                """,
                url,
                selected_relation.order,
            )

        return format_html(
            """
            <a
                href="{}"
                title="Click to add to Selected Memories"
                style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    gap:5px;
                    min-width:106px;
                    height:32px;
                    padding:0 12px;
                    border-radius:999px;
                    border:1px solid rgba(96,165,250,.30);
                    background:rgba(37,99,235,.08);
                    color:#60A5FA;
                    font-size:11px;
                    font-weight:800;
                    letter-spacing:.035em;
                    text-decoration:none;
                    box-sizing:border-box;
                    white-space:nowrap;
                "
            >
                + SELECT
            </a>
            """,
            url,
        )

    # =========================================================================
    # FEATURED TOGGLE
    # =========================================================================

    def toggle_featured_view(
        self,
        request,
        photo_id,
    ):
        photo = get_object_or_404(
            Photo,
            pk=photo_id,
        )

        photo.is_featured = (
            not photo.is_featured
        )

        photo.save(
            update_fields=(
                "is_featured",
                "updated_at",
            )
        )

        if photo.is_featured:
            self.message_user(
                request,
                (
                    f'"{photo.title}" is now Featured.'
                ),
                level=messages.SUCCESS,
            )

        else:
            self.message_user(
                request,
                (
                    f'"{photo.title}" removed from Featured.'
                ),
                level=messages.SUCCESS,
            )

        return self._return_to_photo_list(
            request
        )

    # =========================================================================
    # ATLAS TOGGLE
    # =========================================================================

    def toggle_atlas_view(
        self,
        request,
        photo_id,
    ):
        photo = get_object_or_404(
            Photo.objects.select_related(
                "category"
            ),
            pk=photo_id,
        )

        # ------------------------------------------------------------
        # REMOVE
        # ------------------------------------------------------------

        if photo.show_in_atlas:
            photo.show_in_atlas = False

            photo.save(
                update_fields=(
                    "show_in_atlas",
                    "updated_at",
                )
            )

            self.message_user(
                request,
                (
                    f'"{photo.title}" removed '
                    "from Memory Atlas."
                ),
                level=messages.SUCCESS,
            )

            return self._return_to_photo_list(
                request
            )

        # ------------------------------------------------------------
        # APPROVED REQUIRED
        # ------------------------------------------------------------

        if photo.status != "approved":
            self.message_user(
                request,
                (
                    "Approve this photograph first. "
                    "Only Approved photos can be used "
                    "inside Memory Atlas."
                ),
                level=messages.ERROR,
            )

            return self._return_to_photo_list(
                request
            )

        # ------------------------------------------------------------
        # CATEGORY REQUIRED
        # ------------------------------------------------------------

        if not photo.category:
            self.message_user(
                request,
                (
                    "Assign a Category first. "
                    "Memory Atlas cover photographs "
                    "must belong to a category."
                ),
                level=messages.ERROR,
            )

            return self._return_to_photo_list(
                request
            )

        # ------------------------------------------------------------
        # MAXIMUM 4 PER CATEGORY
        # ------------------------------------------------------------

        current_atlas_count = (
            Photo.objects
            .filter(
                category=photo.category,
                status="approved",
                show_in_atlas=True,
            )
            .exclude(
                pk=photo.pk
            )
            .count()
        )

        if current_atlas_count >= 4:
            self.message_user(
                request,
                (
                    f'"{photo.category.name}" already has '
                    "4 Memory Atlas cover photographs. "
                    "Remove one Atlas photo before adding another."
                ),
                level=messages.ERROR,
            )

            return self._return_to_photo_list(
                request
            )

        # ------------------------------------------------------------
        # ENABLE
        # ------------------------------------------------------------

        photo.show_in_atlas = True

        photo.save(
            update_fields=(
                "show_in_atlas",
                "updated_at",
            )
        )

        self.message_user(
            request,
            (
                f'"{photo.title}" added to '
                f'"{photo.category.name}" Memory Atlas.'
            ),
            level=messages.SUCCESS,
        )

        return self._return_to_photo_list(
            request
        )

    # =========================================================================
    # SELECTED MEMORY TOGGLE
    # =========================================================================

    def toggle_selected_memory_view(
        self,
        request,
        photo_id,
    ):
        photo = get_object_or_404(
            Photo,
            pk=photo_id,
        )

        selected_relation = (
            SelectedGalleryPhoto.objects
            .filter(
                photo=photo,
                is_active=True,
            )
            .first()
        )

        # ------------------------------------------------------------
        # REMOVE
        # ------------------------------------------------------------

        if selected_relation:
            selected_relation.delete()

            self.message_user(
                request,
                (
                    f'"{photo.title}" removed '
                    "from Selected Memories."
                ),
                level=messages.SUCCESS,
            )

            return self._return_to_photo_list(
                request
            )

        # ------------------------------------------------------------
        # APPROVED REQUIRED
        # ------------------------------------------------------------

        if photo.status != "approved":
            self.message_user(
                request,
                (
                    "Approve this photograph first. "
                    "Only Approved photos can be added "
                    "to Selected Memories."
                ),
                level=messages.ERROR,
            )

            return self._return_to_photo_list(
                request
            )

        active_qs = (
            SelectedGalleryPhoto.objects
            .filter(
                is_active=True
            )
        )

        # ------------------------------------------------------------
        # MAXIMUM 10
        # ------------------------------------------------------------

        if active_qs.count() >= 10:
            self.message_user(
                request,
                (
                    "Selected Memories already contains "
                    "10 active photographs. "
                    "Remove one before selecting another."
                ),
                level=messages.ERROR,
            )

            return self._return_to_photo_list(
                request
            )

        # ------------------------------------------------------------
        # FIND FIRST AVAILABLE POSITION
        # ------------------------------------------------------------

        used_orders = set(
            active_qs.values_list(
                "order",
                flat=True,
            )
        )

        available_orders = [
            position
            for position in range(
                1,
                11,
            )
            if position not in used_orders
        ]

        if not available_orders:
            self.message_user(
                request,
                (
                    "All Selected Memory positions "
                    "1–10 are currently occupied."
                ),
                level=messages.ERROR,
            )

            return self._return_to_photo_list(
                request
            )

        selected_order = (
            available_orders[0]
        )

        # ------------------------------------------------------------
        # CREATE / RE-ENABLE
        # ------------------------------------------------------------

        SelectedGalleryPhoto.objects.update_or_create(
            photo=photo,
            defaults={
                "order": selected_order,
                "is_active": True,
            },
        )

        self.message_user(
            request,
            (
                f'"{photo.title}" added to '
                "Selected Memories "
                f"at position #{selected_order}."
            ),
            level=messages.SUCCESS,
        )

        return self._return_to_photo_list(
            request
        )

    # =========================================================================
    # INTERACTIVE LIST TOGGLE CONTROLS
    # =========================================================================

    @admin.display(description="Active")
    def toggle_is_active(self, obj):
        is_on = obj.is_active
        bg = "#10B981" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="is_active"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
            </button>
            '''
        )

    @admin.display(description="Featured")
    def toggle_is_featured(self, obj):
        is_on = obj.is_featured
        bg = "#10B981" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="is_featured"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
            </button>
            '''
        )

    @admin.display(description="Atlas")
    def toggle_show_atlas(self, obj):
        is_on = obj.show_in_atlas
        bg = "#10B981" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="show_in_atlas"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
            </button>
            '''
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category", "uploaded_by").annotate(
            _has_selected=Exists(
                SelectedGalleryPhoto.objects.filter(photo_id=OuterRef("pk"), is_active=True)
            ),
            _has_fragments=Exists(
                ScrapbookPlacement.objects.filter(photo_id=OuterRef("pk"), section="mosaic", is_active=True)
            ),
            _has_film1=Exists(
                ScrapbookPlacement.objects.filter(photo_id=OuterRef("pk"), section="film", film_strip=1, is_active=True)
            ),
            _has_film2=Exists(
                ScrapbookPlacement.objects.filter(photo_id=OuterRef("pk"), section="film", film_strip=2, is_active=True)
            ),
        )

    @admin.display(description="Selected")
    def toggle_selected(self, obj):
        is_on = getattr(obj, "_has_selected", False) if hasattr(obj, "_has_selected") else SelectedGalleryPhoto.objects.filter(photo=obj, is_active=True).exists()
        bg = "#10B981" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="selected"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
            </button>
            '''
        )

    @admin.display(description="Scrapbook")
    def toggle_scrapbook(self, obj):
        sp = ScrapbookPlacement.objects.filter(photo=obj, is_active=True).first()
        is_on = bool(sp)
        bg = "#D7B377" if is_on else "#334155"
        sec_label = sp.section.upper() if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="scrapbook"
                style="display:inline-flex; align-items:center; min-width:62px; height:24px; padding:2px 4px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:8px; font-weight:800; color:#FFF; margin:0 3px;">{sec_label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3); flex-shrink:0;"></span>
            </button>
            '''
        )

    @admin.display(description="Fragments")
    def toggle_fragments(self, obj):
        is_on = getattr(obj, "_has_fragments", False) if hasattr(obj, "_has_fragments") else ScrapbookPlacement.objects.filter(photo=obj, section="mosaic", is_active=True).exists()
        bg = "#C5A3E6" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="memory_fragments"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3); flex-shrink:0;"></span>
            </button>
            '''
        )

    @admin.display(description="Film 1")
    def toggle_film_strip_1(self, obj):
        is_on = getattr(obj, "_has_film1", False) if hasattr(obj, "_has_film1") else ScrapbookPlacement.objects.filter(photo=obj, section="film", film_strip=1, is_active=True).exists()
        bg = "#60A5FA" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="film_strip_1"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3); flex-shrink:0;"></span>
            </button>
            '''
        )

    @admin.display(description="Film 2")
    def toggle_film_strip_2(self, obj):
        is_on = getattr(obj, "_has_film2", False) if hasattr(obj, "_has_film2") else ScrapbookPlacement.objects.filter(photo=obj, section="film", film_strip=2, is_active=True).exists()
        bg = "#3B82F6" if is_on else "#334155"
        label = "ON" if is_on else "OFF"
        align = "flex-end" if is_on else "flex-start"
        return mark_safe(
            f'''
            <button type="button" class="js-admin-toggle" data-photo-id="{obj.pk}" data-field="film_strip_2"
                style="display:inline-flex; align-items:center; width:54px; height:24px; padding:2px; border-radius:999px; background:{bg}; border:none; cursor:pointer; justify-content:{align}; transition:all 200ms ease;">
                <span style="font-size:9px; font-weight:800; color:#FFF; margin:0 4px;">{label}</span>
                <span style="width:18px; height:18px; border-radius:50%; background:#FFF; box-shadow:0 1px 3px rgba(0,0,0,0.3); flex-shrink:0;"></span>
            </button>
            '''
        )

    # =========================================================================
    # EDIT PAGE SELECTED MEMORY & SCRAPBOOK SYNC
    # =========================================================================

    def save_related(
        self,
        request,
        form,
        formsets,
        change,
    ):
        super().save_related(
            request,
            form,
            formsets,
            change,
        )

        photo = form.instance

        if photo and photo.pk:
            in_selected = form.cleaned_data.get("selected_memories") or form.cleaned_data.get("in_selected_memory") or False
            selected_order = form.cleaned_data.get("selected_memories_order") or form.cleaned_data.get("selected_memory_order") or 0

            in_scrapbook = form.cleaned_data.get("in_scrapbook", False)
            scrapbook_section = form.cleaned_data.get("scrapbook_section", "")
            scrapbook_rotation = form.cleaned_data.get("scrapbook_rotation", 0)
            scrapbook_order = form.cleaned_data.get("scrapbook_order", 0)
            scrapbook_custom_title = form.cleaned_data.get("scrapbook_custom_title", "")
            scrapbook_custom_caption = form.cleaned_data.get("scrapbook_custom_caption", "")

            with transaction.atomic():
                if in_selected:
                    SelectedGalleryPhoto.objects.update_or_create(
                        photo=photo,
                        defaults={
                            "order": selected_order or 1,
                            "is_active": True,
                        },
                    )
                else:
                    SelectedGalleryPhoto.objects.filter(
                        photo=photo
                    ).delete()

                if in_scrapbook and scrapbook_section:
                    scrapbook_film_strip = form.cleaned_data.get("scrapbook_film_strip") or 1
                    if scrapbook_section == "film":
                        ScrapbookPlacement.objects.update_or_create(
                            photo=photo,
                            section="film",
                            film_strip=scrapbook_film_strip,
                            defaults={
                                "rotation": scrapbook_rotation or 0,
                                "display_order": scrapbook_order or 0,
                                "custom_title": scrapbook_custom_title or "",
                                "custom_caption": scrapbook_custom_caption or "",
                                "is_active": True,
                            },
                        )
                    else:
                        ScrapbookPlacement.objects.update_or_create(
                            photo=photo,
                            section=scrapbook_section,
                            defaults={
                                "rotation": scrapbook_rotation or 0,
                                "display_order": scrapbook_order or 0,
                                "custom_title": scrapbook_custom_title or "",
                                "custom_caption": scrapbook_custom_caption or "",
                                "is_active": True,
                            },
                        )

    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA["css"]
        js = ADMIN_IMAGE_PREVIEW_MEDIA["js"] + ("admin/js/admin_toggles.js",)

    # =========================================================================
    # IMAGE PREVIEW
    # =========================================================================

    @admin.display(
        description="Preview"
    )
    def thumbnail_preview(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.image
        ):
            return "No image"

        return format_html(
            """
            <img
                src="{}"
                alt=""
                style="
                    width:70px;
                    height:55px;
                    object-fit:cover;
                    border-radius:8px;
                    border:1px solid rgba(215,179,119,.18);
                    box-shadow:0 5px 15px rgba(0,0,0,.14);
                "
            />
            """,
            obj.image.url,
        )

    # =========================================================================
    # BULK — APPROVE
    # =========================================================================

    @admin.action(
        description=(
            "Approve selected photos"
        )
    )
    def approve_selected(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            status="approved"
        )

        self.message_user(
            request,
            (
                f"{updated} photo(s) "
                "approved successfully."
            ),
            level=messages.SUCCESS,
        )

    # =========================================================================
    # BULK — REJECT
    # =========================================================================

    @admin.action(
        description=(
            "Reject selected photos"
        )
    )
    def reject_selected(
        self,
        request,
        queryset,
    ):
        # Automatically remove rejected photos
        # from Atlas before rejecting.

        queryset.update(
            show_in_atlas=False
        )

        # Remove from selected-memory table.
        SelectedGalleryPhoto.objects.filter(
            photo__in=queryset
        ).delete()

        updated = queryset.update(
            status="rejected"
        )

        self.message_user(
            request,
            (
                f"{updated} photo(s) rejected. "
                "Atlas and Selected Memory flags "
                "were safely removed."
            ),
            level=messages.SUCCESS,
        )

    # =========================================================================
    # BULK — FEATURED ON
    # =========================================================================

    @admin.action(
        description=(
            "Mark selected photos as Featured"
        )
    )
    def mark_featured(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            is_featured=True
        )

        self.message_user(
            request,
            (
                f"{updated} photo(s) "
                "marked Featured."
            ),
            level=messages.SUCCESS,
        )

    # =========================================================================
    # BULK — FEATURED OFF
    # =========================================================================

    @admin.action(
        description=(
            "Remove selected photos from Featured"
        )
    )
    def remove_featured(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            is_featured=False
        )

        self.message_user(
            request,
            (
                f"{updated} photo(s) "
                "removed from Featured."
            ),
            level=messages.SUCCESS,
        )

    # =========================================================================
    # BULK — ADD TO ATLAS
    # =========================================================================

    @admin.action(
        description=(
            "Add selected approved photos to Memory Atlas"
        )
    )
    def add_to_atlas(
        self,
        request,
        queryset,
    ):
        enabled_count = 0
        skipped_count = 0

        for photo in queryset.select_related(
            "category"
        ):
            if (
                photo.status != "approved"
                or not photo.category
            ):
                skipped_count += 1
                continue

            current_count = (
                Photo.objects
                .filter(
                    category=photo.category,
                    status="approved",
                    show_in_atlas=True,
                )
                .exclude(
                    pk=photo.pk
                )
                .count()
            )

            if current_count >= 4:
                skipped_count += 1
                continue

            if not photo.show_in_atlas:
                photo.show_in_atlas = True

                photo.save(
                    update_fields=(
                        "show_in_atlas",
                        "updated_at",
                    )
                )

                enabled_count += 1

        if skipped_count:
            level = messages.WARNING
        else:
            level = messages.SUCCESS

        self.message_user(
            request,
            (
                f"{enabled_count} photo(s) added to Memory Atlas. "
                f"{skipped_count} photo(s) skipped."
            ),
            level=level,
        )

    # =========================================================================
    # BULK — REMOVE FROM ATLAS
    # =========================================================================

    @admin.action(
        description=(
            "Remove selected photos from Memory Atlas"
        )
    )
    def remove_from_atlas(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            show_in_atlas=False
        )

        self.message_user(
            request,
            (
                f"{updated} photo(s) "
                "removed from Memory Atlas."
            ),
            level=messages.SUCCESS,
        )


# ============================================================================
# TIMELINE EVENT ADMIN
# ============================================================================


@admin.register(TimelineEvent)
class TimelineEventAdmin(ModelAdmin):
    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    formfield_overrides = {
        models.DateField: {
            "widget": UnfoldAdminDateInputWidget,
        },
    }

    list_display = (
        "id",
        "thumbnail_preview",
        "title",
        "category",
        "event_date",
        "display_order",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "title",
    )

    list_editable = (
        "display_order",
    )

    list_filter = (
        "category",
        "event_date",
    )

    search_fields = (
        "title",
        "description",
        "category__name",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "display_order",
        "event_date",
        "id",
    )

    list_per_page = 20

    date_hierarchy = "event_date"

    fieldsets = (
        (
            "Timeline Information",
            {
                "fields": (
                    "title",
                    "description",
                    "category",
                    "event_date",
                    "display_order",
                )
            },
        ),

        (
            "Timeline Image",
            {
                "fields": (
                    "image",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )

    @admin.display(
        description="Preview"
    )
    def thumbnail_preview(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.image
        ):
            return "No image"

        return format_html(
            (
                '<img src="{}" '
                'style="width:75px;height:55px;'
                'object-fit:cover;border-radius:8px;" '
                'alt="">'
            ),
            obj.image.url,
        )


# ============================================================================
# LEGACY / STANDALONE SCRAPBOOK ITEM ADMIN
# ============================================================================


@admin.register(ScrapbookItem)
class ScrapbookItemAdmin(ModelAdmin):
    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    list_display = (
        "id",
        "thumbnail_preview",
        "title",
        "category",
        "rotation",
        "display_order",
        "is_featured",
        "created_at",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "title",
    )

    list_editable = (
        "rotation",
        "display_order",
        "is_featured",
    )

    list_filter = (
        "category",
        "is_featured",
        "created_at",
    )

    search_fields = (
        "title",
        "caption",
        "category__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "display_order",
        "-created_at",
    )

    list_per_page = 20

    fieldsets = (
        (
            "Scrapbook Information",
            {
                "fields": (
                    "title",
                    "caption",
                    "category",
                    "rotation",
                    "display_order",
                    "is_featured",
                )
            },
        ),

        (
            "Scrapbook Image",
            {
                "fields": (
                    "image",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(
        description="Preview"
    )
    def thumbnail_preview(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.image
        ):
            return "No image"

        return format_html(
            (
                '<img src="{}" '
                'style="width:75px;height:55px;'
                'object-fit:cover;border-radius:8px;" '
                'alt="">'
            ),
            obj.image.url,
        )


# ============================================================================
# STUDENT / YEARBOOK ADMIN
# ============================================================================


@admin.register(Student)
class StudentAdmin(ModelAdmin):
    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    list_display = (
        "id",
        "thumbnail_preview",
        "name",
        "nickname",
        "role",
        "display_order",
        "is_featured",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "name",
    )

    list_editable = (
        "display_order",
        "is_featured",
    )

    list_filter = (
        "is_featured",
        "created_at",
    )

    search_fields = (
        "name",
        "nickname",
        "role",
        "quote",
        "bio",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "display_order",
        "name",
    )

    list_per_page = 20

    fieldsets = (
        (
            "Student Information",
            {
                "fields": (
                    "name",
                    "nickname",
                    "role",
                    "quote",
                    "bio",
                    "display_order",
                    "is_featured",
                )
            },
        ),

        (
            "Profile Photo",
            {
                "fields": (
                    "image",
                )
            },
        ),

        (
            "Social Links",
            {
                "fields": (
                    "instagram_url",
                    "linkedin_url",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(
        description="Preview"
    )
    def thumbnail_preview(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.image
        ):
            return "No image"

        return format_html(
            (
                '<img src="{}" '
                'style="width:60px;height:60px;'
                'object-fit:cover;border-radius:50%;" '
                'alt="">'
            ),
            obj.image.url,
        )


# ============================================================================
# VIDEO ADMIN
# ============================================================================


@admin.register(Video)
class VideoAdmin(ModelAdmin):
    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    list_display = (
        "id",
        "thumbnail_preview",
        "title",
        "category",
        "duration",
        "display_order",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "title",
    )

    list_editable = (
        "display_order",
    )

    list_filter = (
        "category",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "category__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "display_order",
        "-created_at",
    )

    list_per_page = 20

    fieldsets = (
        (
            "Video Information",
            {
                "fields": (
                    "title",
                    "description",
                    "category",
                    "duration",
                    "display_order",
                )
            },
        ),

        (
            "Media",
            {
                "fields": (
                    "video_file",
                    "thumbnail",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(
        description="Preview"
    )
    def thumbnail_preview(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.thumbnail
        ):
            return "No thumbnail"

        return format_html(
            (
                '<img src="{}" '
                'style="width:90px;height:55px;'
                'object-fit:cover;border-radius:8px;" '
                'alt="">'
            ),
            obj.thumbnail.url,
        )


# ============================================================================
# HERO SLIDE ADMIN
# ============================================================================


@admin.register(HeroSlide)
class HeroSlideAdmin(ModelAdmin):
    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    list_display = (
        "id",
        "image_preview",
        "title",
        "display_order",
        "is_active",
        "created_at",
    )

    list_editable = (
        "display_order",
        "is_active",
    )

    search_fields = (
        "title",
        "subtitle",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "display_order",
        "created_at",
    )

    fieldsets = (
        (
            "Hero Slide",
            {
                "fields": (
                    "title",
                    "subtitle",
                    "image",
                )
            },
        ),

        (
            "Display Settings",
            {
                "fields": (
                    "display_order",
                    "is_active",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(
        description="Preview"
    )
    def image_preview(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.image
        ):
            return "No image"

        return format_html(
            (
                '<img src="{}" '
                'style="width:90px;height:60px;'
                'object-fit:cover;border-radius:8px;" '
                'alt="">'
            ),
            obj.image.url,
        )


# ============================================================================
# ABOUT PAGE ADMIN
# ============================================================================


@admin.register(AboutPage)
class AboutPageAdmin(ModelAdmin):
    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    list_display = (
        "__str__",
        "story_title",
        "creator_name",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )

    filter_horizontal = (
        "background_photos",
    )

    fieldsets = (
        (
            "Archive Story Section",
            {
                "fields": (
                    "story_badge",
                    "story_title",
                    "story_paragraph_1",
                    "story_paragraph_2",
                    "story_paragraph_3",
                    "story_image",
                    "story_image_alt",
                )
            },
        ),

        (
            "Background Drift Wall Photos",
            {
                "fields": (
                    "background_photos",
                ),
                "description": (
                    "Select existing gallery photos to "
                    "display in the About page drifting "
                    "background wall. If empty, recent "
                    "approved photos will automatically be used."
                ),
            },
        ),

        (
            "Three Information Cards",
            {
                "fields": (
                    "class_info_title",
                    "class_info_text",
                    "archive_title",
                    "archive_text",
                    "accessibility_title",
                    "accessibility_text",
                )
            },
        ),

        (
            "Creator & Developer Section",
            {
                "fields": (
                    "creator_name",
                    "creator_role",
                    "creator_description",
                    "creator_image",
                    "creator_image_alt",
                    "created_for_text",
                )
            },
        ),

        (
            "Gratitude & Acknowledgement Section",
            {
                "fields": (
                    "thanks_badge",
                    "thanks_title",
                    "thanks_text",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(
        self,
        request,
    ):
        if AboutPage.objects.exists():
            return False

        return super().has_add_permission(
            request
        )


# ============================================================================
# CONTACT PAGE ADMIN
# ============================================================================


@admin.register(ContactPage)
class ContactPageAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "intro_title",
        "email",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )

    fieldsets = (
        (
            "Contact Header & Intro",
            {
                "fields": (
                    "intro_badge",
                    "intro_title",
                    "intro_description",
                )
            },
        ),

        (
            "Contact Information & Social Links",
            {
                "fields": (
                    "email",
                    "phone",
                    "location",
                    "social_label_1",
                    "social_url_1",
                    "social_label_2",
                    "social_url_2",
                )
            },
        ),

        (
            "Form Success Response UX",
            {
                "fields": (
                    "success_message",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(
        self,
        request,
    ):
        if ContactPage.objects.exists():
            return False

        return super().has_add_permission(
            request
        )


# ============================================================================
# CONTACT MESSAGE ADMIN
# ============================================================================


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "subject",
        "category",
        "is_read",
        "created_at",
    )

    list_editable = (
        "is_read",
    )

    list_filter = (
        "is_read",
        "category",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "subject",
        "message",
    )

    readonly_fields = (
        "name",
        "email",
        "subject",
        "category",
        "message",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 20


# ============================================================================
# SELECTED GALLERY PHOTO ADMIN
# ============================================================================


@admin.register(SelectedGalleryPhoto)
class SelectedGalleryPhotoAdmin(ModelAdmin):
    list_display = (
        "thumbnail_preview",
        "photo_title",
        "category_name",
        "order",
        "is_active",
        "created_at",
    )

    list_display_links = (
        "thumbnail_preview",
        "photo_title",
    )

    list_editable = (
        "order",
        "is_active",
    )

    list_filter = (
        "is_active",
        "photo__category",
    )

    search_fields = (
        "photo__title",
        "photo__category__name",
    )

    autocomplete_fields = (
        "photo",
    )

    ordering = (
        "order",
        "created_at",
    )

    list_per_page = 20

    @admin.display(
        description="Thumbnail"
    )
    def thumbnail_preview(
        self,
        obj,
    ):
        if (
            obj.photo
            and obj.photo.image
        ):
            return format_html(
                (
                    '<img src="{}" '
                    'style="width:54px;height:40px;'
                    'object-fit:cover;border-radius:5px;" '
                    'alt="">'
                ),
                obj.photo.image.url,
            )

        return "No Image"

    @admin.display(
        description="Photo Title"
    )
    def photo_title(
        self,
        obj,
    ):
        if obj.photo:
            return obj.photo.title

        return "-"

    @admin.display(
        description="Category"
    )
    def category_name(
        self,
        obj,
    ):
        if (
            obj.photo
            and obj.photo.category
        ):
            return (
                obj.photo.category.name
            )

        return "-"


# ============================================================================
# SCRAPBOOK PLACEMENT ADMIN FORM & ADMIN
# ============================================================================


class ScrapbookPlacementForm(forms.ModelForm):
    class Meta:
        model = ScrapbookPlacement
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        photo = cleaned_data.get("photo") or getattr(self.instance, "photo", None)
        section = cleaned_data.get("section") or getattr(self.instance, "section", None)
        film_strip = cleaned_data.get("film_strip")
        is_active = cleaned_data.get("is_active")

        if not photo or not section:
            return cleaned_data

        if section == "film":
            if is_active and not film_strip:
                cleaned_data["film_strip"] = 1
                film_strip = 1

            if film_strip is not None:
                qs = ScrapbookPlacement.objects.filter(photo=photo, section="film", film_strip=film_strip)
                if self.instance and self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    self.add_error("film_strip", f"This photo is already placed in Film Strip {film_strip}.")

                if is_active:
                    cap_qs = ScrapbookPlacement.objects.filter(section="film", film_strip=film_strip, is_active=True)
                    if self.instance and self.instance.pk:
                        cap_qs = cap_qs.exclude(pk=self.instance.pk)
                    if cap_qs.count() >= 10:
                        self.add_error("film_strip", f"Film Strip {film_strip} already contains 10 active photographs.")
        else:
            if film_strip is not None:
                self.add_error("film_strip", "Film Strip can only be assigned to Moving Film Archive memories.")

            qs = ScrapbookPlacement.objects.filter(photo=photo, section=section)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("section", f"This photo already has a placement in section '{section}'.")

        return cleaned_data


@admin.register(ScrapbookPlacement)
class ScrapbookPlacementAdmin(ModelAdmin):
    form = ScrapbookPlacementForm
    list_select_related = ("photo", "photo__category")

    class Media:
        css = ADMIN_IMAGE_PREVIEW_MEDIA[
            "css"
        ]

        js = ADMIN_IMAGE_PREVIEW_MEDIA[
            "js"
        ]

    list_display = (
        "id",
        "thumbnail_preview",
        "photo_title",
        "section_badge",
        "film_strip",
        "display_order",
        "rotation",
        "is_active",
        "updated_at",
    )

    list_display_links = (
        "id",
        "thumbnail_preview",
        "photo_title",
    )

    list_editable = (
        "film_strip",
        "display_order",
        "rotation",
        "is_active",
    )

    list_filter = (
        "section",
        "film_strip",
        "is_active",
        "photo__category",
    )

    search_fields = (
        "photo__title",
        "custom_title",
        "custom_caption",
        "photo__category__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "photo",
    )

    ordering = (
        "section",
        "film_strip",
        "display_order",
        "-created_at",
    )

    list_per_page = 20

    fieldsets = (
        (
            "Memory & Photo Selection",
            {
                "fields": (
                    "photo",
                    "custom_title",
                    "custom_caption",
                ),
                "description": (
                    "Select an approved photo from the Gallery. "
                    "Custom title and caption are optional overrides."
                ),
            },
        ),

        (
            "Section Placement & Display",
            {
                "fields": (
                    "section",
                    "film_strip",
                    "display_order",
                    "rotation",
                    "is_active",
                ),
                "description": (
                    "Choose where this memory appears: "
                    "PINNED / SCRATCH MEMORIES, "
                    "MOVING FILM ARCHIVE, "
                    "MEMORY MOSAIC, "
                    "or FINAL MEMORY."
                ),
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(
        description="Preview"
    )
    def thumbnail_preview(
        self,
        obj=None,
    ):
        if (
            obj
            and obj.photo
            and obj.photo.image
        ):
            return format_html(
                (
                    '<img src="{}" '
                    'style="width:64px;height:44px;'
                    'object-fit:cover;border-radius:6px;" '
                    'alt="">'
                ),
                obj.photo.image.url,
            )

        return "No Image"

    @admin.display(
        description="Photo Title"
    )
    def photo_title(
        self,
        obj=None,
    ):
        if (
            not obj
            or not obj.photo
        ):
            return "-"

        if obj.custom_title:
            return (
                f"{obj.custom_title} "
                f"({obj.photo.title})"
            )

        return obj.photo.title

    @admin.display(
        description="Section Destination"
    )
    def section_badge(
        self,
        obj=None,
    ):
        if not obj:
            return "-"

        section_name = (
            obj.get_section_display()
        )

        background_colors = {
            "pinned": (
                "rgba(215, 179, 119, 0.3)"
            ),

            "film": (
                "rgba(135, 194, 230, 0.3)"
            ),

            "mosaic": (
                "rgba(197, 163, 230, 0.3)"
            ),

            "final": (
                "rgba(230, 200, 135, 0.3)"
            ),
        }

        text_colors = {
            "pinned": "#D7B377",
            "film": "#87C2E6",
            "mosaic": "#C5A3E6",
            "final": "#E6C887",
        }

        background = (
            background_colors.get(
                obj.section,
                "rgba(255,255,255,0.1)",
            )
        )

        color = (
            text_colors.get(
                obj.section,
                "#FFFFFF",
            )
        )

        return format_html(
            """
            <span
                style="
                    display:inline-flex;
                    align-items:center;
                    background:{};
                    color:{};
                    font-weight:700;
                    padding:4px 10px;
                    border-radius:6px;
                    font-size:.72rem;
                    letter-spacing:.05em;
                    text-transform:uppercase;
                    white-space:nowrap;
                "
            >
                {}
            </span>
            """,
            background,
            color,
            section_name,
        )