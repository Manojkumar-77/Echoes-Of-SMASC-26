def site_branding(request):
    """
    Echoes Of SMASC '26 — Centralized Branding Identity System
    Single Source of Truth for brand constants, taglines, and asset mappings.
    """
    return {
        "SITE_NAME": "Echoes Of SMASC '26",
        "SHORT_NAME": "ES26",
        "TAGLINE": "CAPTURE • RELIVE • FOREVER",
        "EMOTIONAL_LINE": "More Than Memories — A Lifetime Of Echoes.",
        "ADMIN_NAME": "Echoes Of SMASC '26 Administration",
        "BRANDING": {
            "name": "Echoes Of SMASC '26",
            "short_name": "ES26",
            "tagline": "CAPTURE • RELIVE • FOREVER",
            "logo_master": "branding/01_MASTER_LOGO/ES26_MASTER_EXACT.png",
            "logo_master_trimmed": "branding/01_MASTER_LOGO/ES26_MASTER_TRIMMED_EXACT.png",
            "logo_dark": "branding/02_LOGO_VARIANTS/ES26_dark_1024.png",
            "logo_cream": "branding/02_LOGO_VARIANTS/ES26_cream_1024.png",
            "logo_rounded": "branding/02_LOGO_VARIANTS/ES26_ROUNDED_512.png",
            "logo_circle": "branding/02_LOGO_VARIANTS/ES26_CIRCLE_512.png",
            "favicon": "branding/04_FAVICONS_PWA/favicon.ico",
            "pwa_180": "branding/04_FAVICONS_PWA/pwa-180x180.png",
            "pwa_192": "branding/04_FAVICONS_PWA/pwa-192x192.png",
            "pwa_512": "branding/04_FAVICONS_PWA/pwa-512x512.png",
            "og_image": "branding/05_WEB_BANNERS/og_1200x630.png",
            "twitter_image": "branding/05_WEB_BANNERS/twitter_x_1500x500.png",
        },
    }

