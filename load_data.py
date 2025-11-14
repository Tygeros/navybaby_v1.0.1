#!/usr/bin/env python3
import os
import sys
import django
import subprocess
from pathlib import Path

DATA_FILE = "data_dump.json"   # đổi nếu file mày tên khác

def main():
    # Kiểm tra file JSON
    if not Path(DATA_FILE).exists():
        print(f"❌ Không tìm thấy file {DATA_FILE}")
        sys.exit(1)

    # Cài đặt Django env
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navybaby.settings")

    try:
        django.setup()
    except Exception as e:
        print("❌ Lỗi setup Django:", e)
        sys.exit(1)

    # Gọi loaddata
    print(f"📥 Đang load dữ liệu từ {DATA_FILE}...")

    command = [
        sys.executable, "manage.py", "loaddata", DATA_FILE
    ]

    subprocess.run(command)

    print("🎉 Load dữ liệu hoàn tất!")

if __name__ == "__main__":
    main()

