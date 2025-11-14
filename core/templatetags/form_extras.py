from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    try:
        existing = field.field.widget.attrs.get('class', '')
        classes = f"{existing} {css}".strip()
        return field.as_widget(attrs={**field.field.widget.attrs, 'class': classes})
    except Exception:
        # Fallback: render normally if anything goes wrong
        return field
