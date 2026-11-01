"""One-off host helper: clear seeded content, then load host_data.json.

cPanel "Run Script":
  /home/ostaserv/ostaapp/host_flush_content.py

Safety rules:
  * Runs inside a single transaction — on any error nothing changes.
  * Refuses to run when real customer requests exist (PROTECT FKs);
    pass --with-requests only to also clear requests + SMS logs
    (intended for local/test databases).
  * Never touches: users, SMS templates, sessions, migrations.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.db import transaction

# Children first, parents last (FK-safe delete order).
CONTENT_ORDER = [
    "Article",
    "ServiceArea",
    "ProblemOption",
    "HomePageItem",
    "HomePageContent",
    "AboutPageContent",
    "ContactPageContent",
    "FAQ",
    "Page",
    "Brand",
    "Service",
]


def delete_all(model):
    deleted, _ = model._base_manager.all().delete()
    if deleted:
        print(f"  {model._meta.label}: {deleted} row(s)")
    return deleted


def main():
    with_requests = "--with-requests" in sys.argv[1:]

    request_model = apps.get_model("requests", "ServiceRequest")
    existing_requests = request_model._base_manager.count()

    if existing_requests and not with_requests:
        print(f"STOP: {existing_requests} service request(s) exist in this database.")
        print("The script will NOT touch customer requests. If these are test")
        print("requests and you also want them cleared, run again with:")
        print("  --with-requests")
        sys.exit(1)

    with transaction.atomic():
        if with_requests and existing_requests:
            print("Deleting requests + related data (--with-requests) ...")
            for app_label, name in [
                ("requests", "RequestImage"),
                ("requests", "RequestNote"),
                ("requests", "RequestStatusHistory"),
                ("notifications", "SmsLog"),
            ]:
                delete_all(apps.get_model(app_label, name))
            delete_all(request_model)

        print("Deleting old content rows ...")
        for name in CONTENT_ORDER:
            try:
                model = apps.get_model("content", name)
            except LookupError:
                continue
            delete_all(model)
        try:
            model = apps.get_model("core", "SiteSettings")
        except LookupError:
            model = None
        if model is not None:
            delete_all(model)

        print("Loading host_data.json ...")
        call_command("loaddata", "host_data.json", verbosity=1)
    print("SYNC OK.")


if __name__ == "__main__":
    main()
