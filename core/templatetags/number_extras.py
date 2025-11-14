from django import template
import re
from django.utils.safestring import mark_safe
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse

register = template.Library()

THRESHOLD = 1_000_000  # compact when abs(value) >= 1M


def _compact_number(value, digits=1):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value

    sign = '-' if n < 0 else ''
    n = abs(n)

    # Vietnamese context: K, M, B for nghìn, triệu, tỷ
    if n >= 1_000_000_000:
        num = n / 1_000_000_000
        suffix = 'B'
    elif n >= 1_000_000:
        num = n / 1_000_000
        suffix = 'M'
    elif n >= 1_000:
        num = n / 1_000
        suffix = 'K'
    else:
        # No suffix; return integer with thousands separator
        return f"{sign}{intcomma(int(round(n, 0)))}"

    fmt = f"{num:.{digits}f}".rstrip('0').rstrip('.')
    return f"{sign}{fmt}{suffix}"


@register.filter(name='smart_compact')
def smart_compact(value, digits=1):
    """Compact only when the absolute value is large. Otherwise, normal int with commas.
    - digits: number of decimals to keep when compacting
    """
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value

    if abs(n) >= THRESHOLD:
        return _compact_number(n, digits)
    return intcomma(int(round(n, 0)))


@register.filter(name='smart_vnd')
def smart_vnd(value, digits=1):
    """Format VND with full number (no compact K/M/B), appending 'đ'.
    - Always use thousands separator via intcomma.
    - Preserves minus sign for negatives.
    """
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value
    sign = '-' if n < 0 else ''
    return mark_safe(f"{sign}{intcomma(int(round(abs(n), 0)))}đ")


@register.filter(name='sub')
def sub(a, b):
    """Subtract b from a, tolerant of None and strings. Returns numeric result.
    Usage in templates: {{ value1|sub:value2 }}
    """
    try:
        x = float(a or 0)
    except (TypeError, ValueError):
        x = 0.0
    try:
        y = float(b or 0)
    except (TypeError, ValueError):
        y = 0.0
    return x - y


@register.filter(name='sum_attr')
def sum_attr(items, attr):
    try:
        iterable = list(items) if items is not None else []
    except TypeError:
        iterable = []
    total = 0
    for obj in iterable:
        val = None
        try:
            val = getattr(obj, attr)
        except Exception:
            try:
                val = obj.get(attr)
            except Exception:
                val = None
        try:
            total += int(val or 0)
        except Exception:
            try:
                total += int(float(val))
            except Exception:
                total += 0
    return total


def _dig_attr(obj, path):
    parts = (path or '').split('.') if path else []
    cur = obj
    for part in parts:
        if cur is None:
            return None
        try:
            cur = getattr(cur, part)
        except Exception:
            try:
                cur = cur.get(part)
            except Exception:
                return None
    return cur


@register.filter(name='sort_by')
def sort_by(iterable, attr_path):
    try:
        seq = list(iterable)
    except TypeError:
        return iterable

    def key_fn(x):
        v = _dig_attr(x, attr_path)
        # Normalize for None and case-insensitive compare for strings
        if v is None:
            return (1, '')
        if isinstance(v, str):
            return (0, v.lower())
        return (0, v)

    try:
        return sorted(seq, key=key_fn)
    except Exception:
        return seq


@register.filter(name='group_color_size')
def group_color_size(iterable):
    try:
        seq = list(iterable)
    except TypeError:
        return []

    from collections import defaultdict

    acc = defaultdict(lambda: {"order_count": 0, "amount_sum": 0})
    for o in seq:
        try:
            color_name = getattr(getattr(o, 'color', None), 'name', None)
        except Exception:
            color_name = None
        try:
            size_name = getattr(getattr(o, 'size', None), 'name', None)
        except Exception:
            size_name = None
        key = ((color_name or '-'), (size_name or '-'))
        bucket = acc[key]
        bucket["order_count"] += 1
        try:
            amt = getattr(o, 'amount', 0) or 0
        except Exception:
            amt = 0
        try:
            bucket["amount_sum"] += int(amt)
        except Exception:
            try:
                bucket["amount_sum"] += int(float(amt))
            except Exception:
                pass

    items = []
    for (cname, sname), v in acc.items():
        items.append({
            "color": cname,
            "size": sname,
            "order_count": v["order_count"],
            "amount_sum": v["amount_sum"],
        })

    items.sort(key=lambda x: (str(x["color"]).lower(), str(x["size"]).lower()))
    return items


CUSTOMER_CODE_REGEX = re.compile(r"\b(KH-\d{6}-\d{3})\b")


@register.filter(name='link_customer_codes')
def link_customer_codes(value):
    """Convert KH-######-### patterns into links to customers:customer_detail."""
    if not value:
        return value

    def repl(match):
        code = match.group(1)
        try:
            url = reverse('customers:customer_detail', kwargs={'code': code})
        except Exception:
            return code
        return f'<a href="{url}" class="text-blue-400 hover:text-blue-300 underline underline-offset-2">{code}</a>'

    result = CUSTOMER_CODE_REGEX.sub(repl, str(value))
    return mark_safe(result)
