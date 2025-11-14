import re
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()

# Pattern for customer code like KH-101125-009
CUSTOMER_CODE_REGEX = re.compile(r"\b(KH-\d{6}-\d{3})\b")

@register.filter(name='link_customer_codes')
def link_customer_codes(value):
    if not value:
        return value

    def repl(match):
        code = match.group(1)
        try:
            url = reverse('customers:customer_detail', kwargs={'code': code})
        except Exception:
            # If reversing fails, just return the original text
            return code
        return f'<a href="{url}" class="text-blue-400 hover:text-blue-300 underline underline-offset-2">{code}</a>'

    result = CUSTOMER_CODE_REGEX.sub(repl, str(value))
    return mark_safe(result)
