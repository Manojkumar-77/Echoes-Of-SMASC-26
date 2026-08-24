from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.core.mail import send_mail
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Min, Max, Q
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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


# ============================================================
# HOME
# ============================================================


def home(request):
    hero_slides = list(
        HeroSlide.objects
        .filter(is_active=True)
        .order_by(
            "display_order",
            "created_at",
        )
    )

    # ========================================================
    # FEATURED BEST MOMENTS PHOTOGRAPHS (CMS is_featured=True)
    # ========================================================
    featured_photos = list(
        Photo.objects
        .filter(
            status="approved",
            is_active=True,
            is_featured=True,
        )
        .select_related("category")
        .order_by("home_order", "-created_at")
    )

    # Fallback to approved photos if none are explicitly marked featured yet
    if not featured_photos:
        featured_photos = list(
            Photo.objects
            .filter(
                status="approved",
                is_active=True,
            )
            .select_related("category")
            .order_by("home_order", "-created_at")[:12]
        )

    featured_memories = []
    for photo in featured_photos:
        image_url = photo.image.url if photo.image else "/static/branding/02_LOGO_VARIANTS/ES26_ROUNDED_512.png"

        featured_memories.append(
            {
                "id": photo.id,
                "type": "Photo",
                "title": photo.title,
                "image_url": image_url,
                "category": (
                    photo.category.name
                    if photo.category
                    else "Memory"
                ),
                "caption": photo.caption or "",
                "date_sort": (
                    photo.event_date
                    or (
                        photo.created_at.date()
                        if photo.created_at
                        else None
                    )
                ),
                "date_display": (
                    photo.event_date.strftime("%b %Y")
                    if photo.event_date
                    else (
                        photo.created_at.strftime("%b %Y")
                        if photo.created_at
                        else ""
                    )
                ),
                "display_order": photo.home_order or 9999,
                "created_at": photo.created_at,
            }
        )

    latest_photos = (
        Photo.objects
        .filter(
            status="approved",
            is_active=True,
        )
        .select_related("category")
        .order_by("-created_at")[:8]
    )

    featured_events = (
        TimelineEvent.objects
        .filter(is_featured=True)
        .select_related("category")
        .order_by(
            "display_order",
            "event_date",
        )
    )

    featured_students = (
        Student.objects
        .filter(is_featured=True)
        .order_by(
            "display_order",
            "name",
        )[:4]
    )

    featured_videos = (
        Video.objects
        .filter(is_featured=True)
        .select_related("category")
        .order_by(
            "display_order",
            "-created_at",
        )
    )

    context = {
        "hero_slides": hero_slides,
        "featured_memories": featured_memories,
        "featured_photos": featured_memories,
        "latest_photos": latest_photos,
        "featured_events": featured_events,
        "featured_students": featured_students,
        "featured_videos": featured_videos,
        "photo_count": (
            Photo.objects
            .filter(status="approved", is_active=True)
            .count()
        ),
        "timeline_count": (
            TimelineEvent.objects.count()
        ),
        "student_count": (
            Student.objects.count()
        ),
        "video_count": (
            Video.objects.count()
        ),
    }

    return render(
        request,
        "index.html",
        context,
    )


# ============================================================
# GALLERY
# ============================================================



_GALLERY_PAGE_SIZE = 30


def gallery(request):
    """
    Gallery Architecture
    ========================================================

    MEMORY ATLAS
    --------------------------------------------------------
    Every category containing approved photographs receives
    a Memory Atlas portal.

    Portal memory count:
        ALL approved photos in that category — from DB COUNT.

    Portal cover stack:
        ONLY approved photographs where:
            show_in_atlas=True

    Maximum visible Atlas covers:
        4

    NORMAL GALLERY
    --------------------------------------------------------
    Atlas selection does NOT remove a photograph from Gallery.
    Initial page load renders _GALLERY_PAGE_SIZE photos.
    Subsequent pages are fetched via the gallery_photos_api view.

    SELECTED MOMENTS
    --------------------------------------------------------
    Managed independently using SelectedGalleryPhoto.
    """

    selected_category_slug = (
        request.GET
        .get(
            "category",
            "",
        )
        .strip()
    )

    page_num = request.GET.get("page", 1)
    try:
        page_num = max(1, int(page_num))
    except (ValueError, TypeError):
        page_num = 1

    # ========================================================
    # CATEGORIES
    # ========================================================

    # Annotated with photo counts and date ranges via the DB.
    # No in-memory photo list required for Atlas construction.

    categories_qs = (
        Category.objects
        .filter(
            photos__status="approved",
            photos__is_active=True,
            photos__show_gallery=True,
        )
        .annotate(
            photo_count=Count(
                "photos",
                filter=Q(
                    photos__status="approved",
                    photos__is_active=True,
                    photos__show_gallery=True,
                ),
                distinct=True,
            ),
            min_event_date=Min(
                "photos__event_date",
                filter=Q(
                    photos__status="approved",
                    photos__is_active=True,
                    photos__show_gallery=True,
                ),
            ),
            max_event_date=Max(
                "photos__event_date",
                filter=Q(
                    photos__status="approved",
                    photos__is_active=True,
                    photos__show_gallery=True,
                ),
            ),
        )
        .distinct()
        .order_by("name")
    )

    categories = list(categories_qs)

    # ========================================================
    # MEMORY ATLAS PORTALS
    # ========================================================

    atlas_portals = []
    category_map = {}

    for category in categories:

        # --------------------------------------------------------
        # DATE RANGE (from DB annotations — no full photo load)
        # --------------------------------------------------------

        min_date = category.min_event_date
        max_date = category.max_event_date

        if min_date and max_date:
            min_year = min_date.year
            max_year = max_date.year

            if min_year == max_year:
                date_range = str(min_year)
            else:
                date_range = f"{min_year} — {max_year}"

        else:
            date_range = "2024 — 2026"

        # --------------------------------------------------------
        # ATLAS COVER PHOTOS (small targeted query, max 4)
        # --------------------------------------------------------

        atlas_cover_photos = list(
            Photo.objects
            .filter(
                category=category,
                status="approved",
                is_active=True,
                show_gallery=True,
                show_in_atlas=True,
            )
            .select_related("category")
            .order_by("-created_at", "-id")
            [:4]
        )

        portal_data = {
            "category": category,
            "photo_count": category.photo_count,
            "date_range": date_range,
            "cover_photos": atlas_cover_photos,
            "index_num": f"{len(atlas_portals) + 1:02d}",
        }

        atlas_portals.append(portal_data)
        category_map[category.slug] = portal_data

    # ========================================================
    # TOTAL PHOTO COUNT
    # ========================================================

    total_photo_count = sum(
        p.photo_count for p in categories
    )

    # ========================================================
    # MAIN GALLERY STREAM (server-side paginated)
    # ========================================================

    active_category = None

    stream_queryset = (
        Photo.objects
        .filter(
            status="approved",
            is_active=True,
            show_gallery=True,
        )
        .select_related("category", "uploaded_by")
        .order_by("-created_at", "-id")
    )

    if (
        selected_category_slug
        and selected_category_slug in category_map
    ):
        active_category = (
            category_map[selected_category_slug]["category"]
        )
        stream_queryset = stream_queryset.filter(
            category=active_category
        )

    paginator = Paginator(stream_queryset, _GALLERY_PAGE_SIZE)
    page_obj = paginator.get_page(page_num)
    stream_photos = list(page_obj)

    has_more = page_obj.has_next()
    next_page = (
        page_obj.next_page_number()
        if page_obj.has_next()
        else None
    )

    # ========================================================
    # SELECTED MEMORIES
    # ========================================================

    selected_memories = list(
        SelectedGalleryPhoto.objects
        .filter(
            is_active=True,
            photo__status="approved",
            photo__is_active=True,
        )
        .select_related(
            "photo",
            "photo__category",
        )
        .order_by(
            "order",
            "created_at",
        )[:10]
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "gallery.html",
        {
            "photos": stream_photos,

            "categories": categories,

            "atlas_portals": atlas_portals,

            "active_category": active_category,

            "selected_category_slug": (
                selected_category_slug
            ),

            "total_photo_count": (
                total_photo_count
            ),

            "selected_memories": (
                selected_memories
            ),

            # Pagination context
            "has_more": has_more,
            "next_page": next_page,
            "current_page": page_num,
        },
    )


# ============================================================
# GALLERY PHOTOS API  (AJAX Load More)
# ============================================================


def gallery_photos_api(request):
    """
    Paginated JSON endpoint for Gallery Load More.

    GET /gallery/photos/?page=2&category=<slug>

    Returns:
        {
            "photos": [...],
            "has_more": bool,
            "next_page": int | null,
            "total": int
        }
    """

    page_num = request.GET.get("page", 1)
    try:
        page_num = max(1, int(page_num))
    except (ValueError, TypeError):
        page_num = 1

    category_slug = (
        request.GET.get("category", "").strip()
    )

    queryset = (
        Photo.objects
        .filter(
            status="approved",
            is_active=True,
            show_gallery=True,
        )
        .select_related("category")
        .order_by("-created_at", "-id")
    )

    if category_slug:
        queryset = queryset.filter(
            category__slug=category_slug
        )

    paginator = Paginator(queryset, _GALLERY_PAGE_SIZE)
    page_obj = paginator.get_page(page_num)

    photos_data = []
    for photo in page_obj:
        photos_data.append({
            "id": photo.id,
            "title": photo.title or "",
            "caption": photo.caption or "",
            "alt_text": photo.alt_text or photo.title or "",
            "image_url": (
                photo.image.url if photo.image else ""
            ),
            "category_name": (
                photo.category.name
                if photo.category
                else "Gallery"
            ),
            "event_date": (
                photo.event_date.strftime("%d %b %Y")
                if photo.event_date
                else (
                    photo.created_at.strftime("%d %b %Y")
                    if photo.created_at
                    else ""
                )
            ),
        })

    return JsonResponse(
        {
            "photos": photos_data,
            "has_more": page_obj.has_next(),
            "next_page": (
                page_obj.next_page_number()
                if page_obj.has_next()
                else None
            ),
            "total": paginator.count,
        }
    )





def timeline(request):
    all_events = list(
        TimelineEvent.objects
        .select_related("category")
        .order_by(
            "display_order",
            "event_date",
        )
    )

    categories = list(
        Category.objects
        .filter(
            timeline_events__isnull=False
        )
        .distinct()
        .order_by("name")
    )

    timeline_groups = []

    # ========================================================
    # CATEGORIZED TIMELINE EVENTS
    # ========================================================

    for category in categories:
        category_events = [
            event
            for event in all_events
            if event.category_id
            == category.id
        ]

        if not category_events:
            continue

        primary_event = (
            category_events[0]
        )

        image_events = []

        seen_images = set()

        for event in category_events:
            if not event.image:
                continue

            image_key = (
                event.image.name
            )

            if image_key in seen_images:
                continue

            seen_images.add(
                image_key
            )

            image_events.append(
                event
            )

            if len(image_events) == 4:
                break

        timeline_groups.append(
            {
                "category": category,
                "primary_event": primary_event,
                "image_events": image_events,
            }
        )

    # ========================================================
    # UNCATEGORIZED TIMELINE EVENTS
    # ========================================================

    uncategorized_events = [
        event
        for event in all_events
        if event.category_id is None
    ]

    if uncategorized_events:
        primary_event = (
            uncategorized_events[0]
        )

        image_events = []

        seen_images = set()

        for event in uncategorized_events:
            if not event.image:
                continue

            image_key = (
                event.image.name
            )

            if image_key in seen_images:
                continue

            seen_images.add(
                image_key
            )

            image_events.append(
                event
            )

            if len(image_events) == 4:
                break

        timeline_groups.append(
            {
                "category": None,
                "primary_event": primary_event,
                "image_events": image_events,
            }
        )

    return render(
        request,
        "timeline.html",
        {
            "timeline_groups": (
                timeline_groups
            ),

            "categories": categories,
        },
    )


# ============================================================
# SCRAPBOOK
# ============================================================


def scrapbook(request):
    """
    Current Scrapbook pipeline.

    Existing ScrapbookItem content is preserved.

    ScrapbookPlacement -> Photo remains the configurable
    placement system for:
        - pinned
        - film
        - mosaic
        - final
    """

    # ========================================================
    # 1. LEGACY / SCRATCH ITEMS
    # ========================================================

    items = (
        ScrapbookItem.objects
        .select_related("category")
        .order_by(
            "display_order",
            "-created_at",
        )
    )

    # ========================================================
    # 2. ACTIVE SCRAPBOOK PLACEMENTS (EXPLICIT ONLY)
    # ========================================================

    placements = list(
        ScrapbookPlacement.objects
        .filter(
            is_active=True,
            photo__status="approved",
            photo__is_active=True,
        )
        .select_related(
            "photo",
            "photo__category",
        )
        .order_by(
            "section",
            "display_order",
            "-created_at",
        )
    )

    pinned_placements = [
        placement
        for placement in placements
        if placement.section == "pinned"
    ]

    film_placements = [
        placement
        for placement in placements
        if placement.section == "film"
    ]

    mosaic_placements = [
        placement
        for placement in placements
        if placement.section == "mosaic"
    ]

    final_placements = [
        placement
        for placement in placements
        if placement.section == "final"
    ]

    # Helper for formatting memory date
    def _get_photo_date(photo):
        if not photo:
            return ""
        if photo.event_date:
            return photo.event_date.strftime("%b %Y")
        if photo.created_at:
            return photo.created_at.strftime("%b %Y")
        return ""

    # ========================================================
    # PINNED ITEMS (EXPLICIT ONLY, NO FALLBACK, NO REPEAT)
    # ========================================================

    pinned_items = []

    if pinned_placements:
        seen_photo_ids = set()
        for placement in pinned_placements:
            if not placement.photo or placement.photo.id in seen_photo_ids:
                continue
            seen_photo_ids.add(placement.photo.id)
            pinned_items.append(
                {
                    "photo": placement.photo,
                    "id": placement.photo.id if placement.photo else placement.id,
                    "title": (
                        placement.custom_title
                        or placement.photo.title
                    ),
                    "caption": (
                        placement.custom_caption
                        or placement.photo.caption
                    ),
                    "image_url": (
                        placement.photo.image.url
                        if placement.photo and placement.photo.image
                        else ""
                    ),
                    "category": (
                        placement.photo.category.name
                        if placement.photo and placement.photo.category
                        else "Fragment"
                    ),
                    "date": _get_photo_date(placement.photo),
                    "rotation": (
                        placement.rotation
                        or 0
                    ),
                    "display_order": (
                        placement.display_order
                    ),
                    "placement_id": (
                        placement.id
                    ),
                }
            )

    # ========================================================
    # FILM STRIP (EXPLICIT STRIP 1 & STRIP 2, MAX 10 EACH)
    # ========================================================

    film_strip1_placements = [
        p for p in placements
        if p.section == "film" and p.film_strip == 1
    ]

    film_strip2_placements = [
        p for p in placements
        if p.section == "film" and p.film_strip == 2
    ]

    row1_base = []
    row2_base = []
    strip1_seen = set()
    strip2_seen = set()

    if film_strip1_placements:
        for index, placement in enumerate(film_strip1_placements, start=1):
            if not placement.photo or placement.photo.id in strip1_seen:
                continue
            strip1_seen.add(placement.photo.id)
            row1_base.append(
                {
                    "photo": placement.photo,
                    "id": placement.photo.id if placement.photo else placement.id,
                    "title": (
                        placement.custom_title
                        or placement.photo.title
                    ),
                    "caption": (
                        placement.custom_caption
                        or placement.photo.caption
                    ),
                    "image_url": (
                        placement.photo.image.url
                        if placement.photo and placement.photo.image
                        else ""
                    ),
                    "category": (
                        placement.photo.category.name
                        if placement.photo and placement.photo.category
                        else "Reel"
                    ),
                    "date": _get_photo_date(placement.photo),
                    "display_num": f"{index:02d}",
                }
            )

    if film_strip2_placements:
        for index, placement in enumerate(film_strip2_placements, start=11):
            if not placement.photo or placement.photo.id in strip2_seen:
                continue
            strip2_seen.add(placement.photo.id)
            row2_base.append(
                {
                    "photo": placement.photo,
                    "id": placement.photo.id if placement.photo else placement.id,
                    "title": (
                        placement.custom_title
                        or placement.photo.title
                    ),
                    "caption": (
                        placement.custom_caption
                        or placement.photo.caption
                    ),
                    "image_url": (
                        placement.photo.image.url
                        if placement.photo and placement.photo.image
                        else ""
                    ),
                    "category": (
                        placement.photo.category.name
                        if placement.photo and placement.photo.category
                        else "Reel"
                    ),
                    "date": _get_photo_date(placement.photo),
                    "display_num": f"{index:02d}",
                }
            )

    film_row1 = row1_base
    film_row2 = row2_base

    # ========================================================
    # MEMORY MOSAIC / MEMORY FRAGMENTS (EXPLICIT ONLY, NO FALLBACK, NO REPEAT)
    # ========================================================

    mosaic_items = []

    if mosaic_placements:
        seen_photo_ids = set()
        for placement in mosaic_placements:
            if not placement.photo or placement.photo.id in seen_photo_ids:
                continue
            seen_photo_ids.add(placement.photo.id)
            mosaic_items.append(
                {
                    "photo": placement.photo,
                    "id": placement.photo.id,
                    "title": (
                        placement.custom_title
                        or placement.photo.title
                    ),
                    "caption": (
                        placement.custom_caption
                        or placement.photo.caption
                    ),
                    "image_url": (
                        placement.photo.image.url
                        if placement.photo and placement.photo.image
                        else ""
                    ),
                    "category": (
                        placement.photo.category.name
                        if placement.photo and placement.photo.category
                        else "Fragment"
                    ),
                    "date": _get_photo_date(placement.photo),
                }
            )

    # ========================================================
    # FINAL MEMORY (EXPLICIT ONLY, NO FALLBACK)
    # ========================================================

    final_item = None

    if final_placements:
        placement = final_placements[0]
        if placement.photo:
            final_item = {
                "photo": placement.photo,
                "id": placement.photo.id if placement.photo else placement.id,
                "title": (
                    placement.custom_title
                    or placement.photo.title
                ),
                "caption": (
                    placement.custom_caption
                    or placement.photo.caption
                ),
                "image_url": (
                    placement.photo.image.url
                    if placement.photo and placement.photo.image
                    else ""
                ),
                "category": (
                    placement.photo.category.name
                    if placement.photo and placement.photo.category
                    else "Class Photo"
                ),
                "date": _get_photo_date(placement.photo),
            }

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "scrapbook.html",
        {
            "items": items,

            "pinned_items": (
                pinned_items
            ),

            "film_row1": film_row1,

            "film_row2": film_row2,

            "mosaic_items": (
                mosaic_items
            ),

            "final_item": final_item,
        },
    )


# ============================================================
# YEARBOOK
# ============================================================


def yearbook(request):
    students = list(
        Student.objects
        .all()
        .order_by(
            "display_order",
            "name",
        )
    )

    # ========================================================
    # ACTIVE ALPHABET INDEX
    # ========================================================

    active_letters = set()

    for student in students:
        if not student.name:
            continue

        first_character = (
            student.name
            .strip()[0]
            .upper()
        )

        if first_character.isalpha():
            active_letters.add(
                first_character
            )

    sorted_active_letters = sorted(
        list(active_letters)
    )

    all_alphabet = [
        chr(character)
        for character in range(
            65,
            91,
        )
    ]

    # ========================================================
    # STRUCTURED STUDENT DATA
    # ========================================================

    size_patterns = [
        "featured",
        "medium",
        "small",
        "medium",
        "small",
    ]

    structured_students = []

    for index, student in enumerate(
        students
    ):
        size_class = (
            size_patterns[
                index
                % len(size_patterns)
            ]
        )

        first_letter = (
            student.name
            .strip()[0]
            .upper()
            if student.name
            else "A"
        )

        structured_students.append(
            {
                "object": student,

                "size_class": (
                    size_class
                ),

                "first_letter": (
                    first_letter
                ),

                "index_num": (
                    f"{index + 1:03d}"
                ),
            }
        )

    return render(
        request,
        "yearbook.html",
        {
            "students": students,

            "structured_students": (
                structured_students
            ),

            "active_letters": (
                sorted_active_letters
            ),

            "all_alphabet": (
                all_alphabet
            ),

            "total_student_count": (
                len(students)
            ),
        },
    )


# ============================================================
# VIDEOS
# ============================================================




_VIDEOS_PAGE_SIZE = 24


def videos(request):
    page_num = request.GET.get("page", 1)
    try:
        page_num = max(1, int(page_num))
    except (ValueError, TypeError):
        page_num = 1

    video_queryset = (
        Video.objects
        .select_related("category")
        .order_by(
            "display_order",
            "-created_at",
        )
    )

    video_categories = list(
        Category.objects
        .filter(
            videos__isnull=False
        )
        .distinct()
        .order_by("name")
    )

    paginator = Paginator(video_queryset, _VIDEOS_PAGE_SIZE)
    page_obj = paginator.get_page(page_num)

    has_more = page_obj.has_next()
    next_page = (
        page_obj.next_page_number()
        if page_obj.has_next()
        else None
    )

    return render(
        request,
        "videos.html",
        {
            "videos": list(page_obj),

            "video_categories": video_categories,

            # Pagination context
            "has_more": has_more,
            "next_page": next_page,
            "current_page": page_num,
            "total_video_count": paginator.count,
        },
    )


# ============================================================
# VIDEOS API  (AJAX Load More)
# ============================================================


def videos_api(request):
    """
    Paginated JSON endpoint for Videos Load More.

    GET /videos/page/?page=2

    Returns:
        {
            "videos": [...],
            "has_more": bool,
            "next_page": int | null,
            "total": int
        }
    """

    page_num = request.GET.get("page", 1)
    try:
        page_num = max(1, int(page_num))
    except (ValueError, TypeError):
        page_num = 1

    queryset = (
        Video.objects
        .select_related("category")
        .order_by("display_order", "-created_at")
    )

    paginator = Paginator(queryset, _VIDEOS_PAGE_SIZE)
    page_obj = paginator.get_page(page_num)

    videos_data = []
    for video in page_obj:
        videos_data.append({
            "id": video.id,
            "title": video.title or "",
            "description": video.description or "",
            "video_url": (
                video.video_file.url if video.video_file else ""
            ),
            "thumbnail_url": (
                video.thumbnail.url if video.thumbnail else ""
            ),
            "category_slug": (
                video.category.slug if video.category else "uncategorized"
            ),
            "category_name": (
                video.category.name if video.category else "Memory"
            ),
            "created_at": (
                video.created_at.strftime("%d %b %Y")
                if video.created_at
                else ""
            ),
            "duration": video.duration or "",
            "is_featured": video.is_featured,
        })

    return JsonResponse(
        {
            "videos": videos_data,
            "has_more": page_obj.has_next(),
            "next_page": (
                page_obj.next_page_number()
                if page_obj.has_next()
                else None
            ),
            "total": paginator.count,
        }
    )


# ============================================================
# ABOUT
# ============================================================


def about(request):
    about_cfg = (
        AboutPage.get_solo()
    )

    # ========================================================
    # ADMIN-SELECTED DRIFT WALL
    # ========================================================

    source_photos = list(
        about_cfg
        .background_photos
        .filter(
            status="approved",
            is_active=True,
        )
        .select_related("category")
    )

    # ========================================================
    # VALID IMAGE URLS
    # ========================================================

    valid_urls = []

    for photo in source_photos:
        if (
            not photo.image
            or not getattr(
                photo.image,
                "url",
                None,
            )
        ):
            continue

        url_string = str(
            photo.image.url
        ).strip()

        if (
            url_string
            and url_string
            not in valid_urls
        ):
            valid_urls.append(
                url_string
            )

    # ========================================================
    # BUILD DRIFT COLUMNS
    # ========================================================

    columns_count = 5

    items_per_column = 10

    drift_columns = []

    if valid_urls:
        drift_columns = [
            []
            for _ in range(
                columns_count
            )
        ]

        url_count = len(
            valid_urls
        )

        for column_index in range(
            columns_count
        ):
            for tile_index in range(
                items_per_column
            ):
                sequence_index = (
                    (
                        column_index * 3
                    )
                    + tile_index
                ) % url_count

                drift_columns[
                    column_index
                ].append(
                    valid_urls[
                        sequence_index
                    ]
                )

    context = {
        "about": about_cfg,

        "drift_columns": (
            drift_columns
        ),

        "valid_photo_urls": (
            valid_urls
        ),

        "photo_count": (
            Photo.objects
            .filter(status="approved")
            .count()
        ),

        "timeline_count": (
            TimelineEvent.objects
            .count()
        ),

        "student_count": (
            Student.objects
            .count()
        ),

        "video_count": (
            Video.objects
            .count()
        ),
    }

    return render(
        request,
        "about.html",
        context,
    )


# ============================================================
# CONTACT
# ============================================================


def contact(request):
    contact_cfg = (
        ContactPage.get_solo()
    )

    form_data = {}

    errors = {}

    # ========================================================
    # FORM SUBMISSION
    # ========================================================

    if request.method == "POST":
        name = (
            request.POST
            .get(
                "name",
                "",
            )
            .strip()
        )

        email = (
            request.POST
            .get(
                "email",
                "",
            )
            .strip()
        )

        subject = (
            request.POST
            .get(
                "subject",
                "",
            )
            .strip()
        )

        category = (
            request.POST
            .get(
                "category",
                "General",
            )
            .strip()
        )

        message_text = (
            request.POST
            .get(
                "message",
                "",
            )
            .strip()
        )

        form_data = {
            "name": name,

            "email": email,

            "subject": subject,

            "category": category,

            "message": message_text,
        }

        # ====================================================
        # SERVER-SIDE VALIDATION
        # ====================================================

        if not name:
            errors["name"] = "Please enter your name."
        elif len(name) > 150:
            errors["name"] = "Name must be 150 characters or fewer."

        if not email:
            errors["email"] = "Please enter a valid email address."
        else:
            try:
                EmailValidator()(email)
            except ValidationError:
                errors["email"] = "Please enter a valid email address."

        if not subject:
            errors["subject"] = "Please enter a subject."
        elif len(subject) > 200:
            errors["subject"] = "Subject must be 200 characters or fewer."

        if not message_text:
            errors["message"] = "Please enter your message."
        elif len(message_text) > 5000:
            errors["message"] = "Message must be 5000 characters or fewer."

        # ====================================================
        # VALID SUBMISSION
        # ====================================================

        if not errors:
            # ------------------------------------------------
            # SAVE MESSAGE
            # ------------------------------------------------

            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                category=category,
                message=message_text,
            )

            # ------------------------------------------------
            # EMAIL NOTIFICATION
            # ------------------------------------------------

            try:
                mail_subject = (
                    f"[Echoes Of SMASC Contact] {subject} ({category})"
                )

                mail_body = (
                    f"Name: {name}\n"
                    f"Email: {email}\n"
                    f"Category: {category}\n"
                    f"Subject: {subject}\n\n"
                    "Message:\n"
                    f"{message_text}"
                )

                sender = getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost")
                recipient = getattr(
                    settings,
                    "CONTACT_NOTIFICATION_EMAIL",
                    sender,
                )

                if sender and recipient:
                    send_mail(
                        mail_subject,
                        mail_body,
                        sender,
                        [recipient],
                        fail_silently=False,
                    )

            except Exception as e:
                # Contact message is already safely persisted to DB
                logger.warning(f"Contact notification email could not be sent: {e}")

            # ------------------------------------------------
            # POST / REDIRECT / GET
            # ------------------------------------------------

            request.session[
                "contact_success"
            ] = True

            return redirect(
                "contact"
            )

    # ========================================================
    # SUCCESS STATE
    # ========================================================

    is_success = (
        request.session.pop(
            "contact_success",
            False,
        )
    )

    context = {
        "contact": contact_cfg,

        "form_data": (
            form_data
            if errors
            else {}
        ),

        "errors": errors,

        "is_success": (
            is_success
        ),
    }

    return render(
        request,
        "contact.html",
        context,
    )


def health_check(request):
    """
    Health check endpoint for Render / PaaS liveness probes and automated tests.
    Always returns HTTP 200 with database connectivity status in JSON payload.
    """
    db_ok = True
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False

    return JsonResponse(
        {
            "status": "ok",
            "database": "connected" if db_ok else "disconnected",
        },
        status=200,
    )