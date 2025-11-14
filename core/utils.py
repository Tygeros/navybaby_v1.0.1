from django.utils import timezone

def generate_code(model_class, prefix):
    now = timezone.now()
    date_prefix = now.strftime("%d%m%y")
    code_prefix = f"{prefix}-{date_prefix}"

    last_obj = model_class.objects.filter(code__startswith=code_prefix).order_by("-code").first()
    last_num = int(last_obj.code.split("-")[-1]) if last_obj else 0

    return f"{code_prefix}-{last_num + 1:03d}"