from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("gallery/", views.gallery, name="gallery"),
    path("gallery/photos/", views.gallery_photos_api, name="gallery_photos_api"),
    path("timeline/", views.timeline, name="timeline"),
    path("scrapbook/", views.scrapbook, name="scrapbook"),
    path("yearbook/", views.yearbook, name="yearbook"),
    path("videos/", views.videos, name="videos"),
    path("videos/page/", views.videos_api, name="videos_api"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("health/", views.health_check, name="health_check"),
]