import os
from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage
from whitenoise.storage import CompressedManifestStaticFilesStorage


class DevAutoVersionStaticFilesStorage(StaticFilesStorage):
    """
    Development Static Files Storage that automatically appends the physical file's
    last modification timestamp (?v=<mtime>) to static URLs when DEBUG=True.
    This guarantees that whenever a CSS or JS file in C:\\P-Gallery\\static is saved,
    the browser receives a unique URL parameter and immediately reloads the updated file.
    """

    def url(self, name):
        url = super().url(name)
        if settings.DEBUG:
            # Construct physical path in C:\P-Gallery\static
            clean_name = name.replace("/", os.sep).replace("\\", os.sep)
            file_path = os.path.join(settings.BASE_DIR, "static", clean_name)
            if os.path.exists(file_path):
                try:
                    mtime = int(os.path.getmtime(file_path))
                    return f"{url}?v={mtime}"
                except OSError:
                    pass
        return url


class ProductionManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Production Static Files Storage using WhiteNoise compression and manifest caching.
    manifest_strict = False ensures that if a static reference or favicon lookup occurs
    before post-processing or without a hashed entry, it safely falls back to the clean static URL
    instead of raising a fatal ValueError.
    """
    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            return name

    def url(self, name, force=False):
        try:
            return super().url(name, force)
        except ValueError:
            return StaticFilesStorage.url(self, name)


