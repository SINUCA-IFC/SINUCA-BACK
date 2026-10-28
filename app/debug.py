import re

from django.views.debug import SafeExceptionReporterFilter


class SensitiveSettingsFilter(SafeExceptionReporterFilter):
    # Cloudinary embeds its credentials in a URL that Django's default filter misses.
    hidden_settings = re.compile(
        SafeExceptionReporterFilter.hidden_settings.pattern + r'|CLOUDINARY_URL',
        re.IGNORECASE,
    )
