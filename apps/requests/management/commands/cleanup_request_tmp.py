"""Delete staged wizard images whose sessions never completed.

Visitors who abandon the request wizard after uploading photos leave those
files under media/tmp/<dir>/ forever. This command removes temp dirs older
than --age-hours (default 24). Run daily from cPanel cron:

    0 3 * * * cd ~/ostaapp && source ~/virtualenv/.../activate \
        && python manage.py cleanup_request_tmp
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path


class Command(BaseCommand):
    help = "Delete abandoned media/tmp upload dirs older than the given age."

    def add_arguments(self, parser):
        parser.add_argument(
            "--age-hours",
            type=int,
            default=24,
            help="Delete temp dirs whose last modification is older than this many hours (default 24).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be deleted.",
        )

    def handle(self, *args, **options):
        age_hours = options["age_hours"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(hours=age_hours)
        tmp_root = Path(settings.MEDIA_ROOT) / "tmp"
        if not tmp_root.exists():
            self.stdout.write("No media/tmp directory — nothing to do.")
            return

        removed = 0
        freed = 0
        for entry in tmp_root.iterdir():
            if not entry.is_dir():
                continue
            try:
                mtime = timezone.make_aware(
                    timezone.datetime.fromtimestamp(entry.stat().st_mtime),
                    timezone.get_current_timezone(),
                )
            except OSError:
                continue
            if mtime >= cutoff:
                continue
            size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
            if dry_run:
                self.stdout.write(f"Would remove {entry.name} ({size} bytes)")
            else:
                import shutil

                shutil.rmtree(entry, ignore_errors=True)
            removed += 1
            freed += size

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry-run] ' if dry_run else ''}Removed {removed} temp dir(s), freed {freed} bytes."
            )
        )
