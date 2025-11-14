from django import template
from django.conf import settings

register = template.Library()

@register.filter
def safe_image_url(image_field):
    """
    Safely get a URL for an ImageField/CloudinaryField.
    - If Cloudinary is configured, use the field's url.
    - If not configured or url building fails, fall back to MEDIA_URL + name.
    - Returns empty string if not available.
    """
    if not image_field:
        return ""
    # Try native .url first (works when configured properly)
    try:
        url = image_field.url
        return url or ""
    except Exception:
        pass
    # Fallback to MEDIA_URL + name
    name = getattr(image_field, "name", "")
    if not name:
        return ""
    # If already a full URL, return as-is
    if isinstance(name, str) and name.startswith("http"):
        return name
    base = getattr(settings, "MEDIA_URL", "/media/")
    if not base.endswith("/"):
        base += "/"
    return f"{base}{name}"
