from django.conf import settings


class DevCacheControlMiddleware:
    """
    Development Middleware that sets strict no-cache headers for static and media
    responses when DEBUG=True, preventing browser disk/memory caching of local files.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if settings.DEBUG:
            path = request.path_info
            if path.startswith(settings.STATIC_URL) or path.startswith(
                settings.MEDIA_URL
            ):
                response["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response["Pragma"] = "no-cache"
                response["Expires"] = "0"

        return response
