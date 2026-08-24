import django.contrib.admin.options

if not hasattr(django.contrib.admin.options, "IS_FACETS_VAR"):
    django.contrib.admin.options.IS_FACETS_VAR = "_facets"
