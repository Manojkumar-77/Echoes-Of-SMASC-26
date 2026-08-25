from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Patch Django BaseContext.flatten to handle nested BaseContext instances
        # gracefully when Unfold components call context.flatten() inside inclusion tags
        # (such as admin/submit_line.html and submit_row).
        import django.template.context

        orig_flatten = django.template.context.BaseContext.flatten

        def robust_flatten(self):
            flat = {}
            for d in self.dicts:
                if isinstance(d, django.template.context.BaseContext):
                    flat.update(d.flatten())
                elif isinstance(d, dict):
                    flat.update(d)
                else:
                    try:
                        flat.update(d)
                    except Exception:
                        pass
            return flat

        django.template.context.BaseContext.flatten = robust_flatten

