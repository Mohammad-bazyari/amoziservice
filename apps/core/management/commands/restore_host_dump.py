"""Restore and migrate a MariaDB/MySQL database dump into the current Django database.

Handles schema evolution (e.g. security questions, brand logo theme) and ensures
all articles, FAQs, requests, settings, and users are properly imported.
"""

import gzip
import os
import re
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


DEFAULT_DUMP_PATH = r"C:/Users/10/.gemini/antigravity/brain/ff1b47d1-4691-4efb-a2f6-1d5b04a5d6e0/.user_uploaded/media_1793702645656_b2385758.gz"

APP_TABLES_ORDERED = [
    # Child / dependent tables first
    "requests_requestimage",
    "requests_requestnote",
    "requests_requeststatushistory",
    "requests_servicerequest",
    "notifications_smslog",
    "notifications_smstemplate",
    "content_article",
    "content_faq",
    "content_page",
    "content_aboutpagecontent",
    "content_contactpagecontent",
    "content_homepageitem",
    "content_homepagecontent",
    "content_problemoption",
    "content_servicearea",
    "content_brand",
    "content_service",
    "core_sitesettings",
    "django_admin_log",
    "django_session",
    "accounts_user_groups",
    "accounts_user_user_permissions",
    "accounts_user",
    "auth_group_permissions",
    "auth_group",
]


class Command(BaseCommand):
    help = "Restore data from a MariaDB/MySQL dump (.sql or .sql.gz) into the active database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="dump_file",
            default=DEFAULT_DUMP_PATH,
            help="Path to SQL or gzipped SQL dump file.",
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Do not clear existing data before importing.",
        )

    def handle(self, *args, **options):
        dump_path = options["dump_file"]
        if not os.path.exists(dump_path):
            raise CommandError(f"Dump file not found: {dump_path}")

        self.stdout.write(f"Reading database dump from: {dump_path}")

        is_sqlite = connection.vendor == "sqlite"

        with connection.cursor() as cursor:
            if is_sqlite:
                cursor.execute("PRAGMA foreign_keys = OFF;")
            else:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            if not options["no_clear"]:
                self.stdout.write("Clearing existing application data...")
                for table in APP_TABLES_ORDERED:
                    try:
                        cursor.execute(f'DELETE FROM "{table}"' if is_sqlite else f"TRUNCATE TABLE `{table}`")
                    except Exception as e:
                        # Fallback for tables that might not exist or foreign key constraints
                        try:
                            cursor.execute(f'DELETE FROM "{table}"' if is_sqlite else f"DELETE FROM `{table}`")
                        except Exception:
                            pass

            self.stdout.write("Parsing dump and inserting records...")
            counts = self._parse_and_insert(dump_path, cursor, is_sqlite)

            if is_sqlite:
                cursor.execute("PRAGMA foreign_keys = ON;")
            else:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        self.stdout.write(self.style.SUCCESS("\nRestoration summary:"))
        for table, count in sorted(counts.items()):
            self.stdout.write(f"  - {table}: {count} records")

        self.stdout.write(self.style.SUCCESS("\nDatabase restored and migrated successfully!"))

    def _parse_and_insert(self, dump_file, cursor, is_sqlite):
        insert_regex = re.compile(r"^INSERT INTO `([^`]+)` \(([^)]+)\) VALUES\s*(.*)$")
        counts = {}

        opener = gzip.open if dump_file.endswith(".gz") else open

        current_table = None
        current_cols = None
        accumulating = False
        buffer = []

        with opener(dump_file, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not accumulating:
                    m = insert_regex.match(line)
                    if m:
                        current_table = m.group(1)
                        cols_str = m.group(2)
                        current_cols = [c.strip().strip("`") for c in cols_str.split(",")]

                        rest = m.group(3)
                        buffer = [rest]
                        accumulating = True
                        if rest.rstrip().endswith(";"):
                            accumulating = False
                            values_text = "".join(buffer)
                            cnt = self._insert_table_data(current_table, current_cols, values_text, cursor, is_sqlite)
                            if cnt:
                                counts[current_table] = counts.get(current_table, 0) + cnt
                else:
                    buffer.append(line)
                    if line.rstrip().endswith(";"):
                        accumulating = False
                        values_text = "".join(buffer)
                        cnt = self._insert_table_data(current_table, current_cols, values_text, cursor, is_sqlite)
                        if cnt:
                            counts[current_table] = counts.get(current_table, 0) + cnt

        return counts

    def _insert_table_data(self, table, cols, values_text, cursor, is_sqlite):
        # Skip django schema internal tracking tables from the old dump so we preserve current migrations
        if table in ["django_migrations", "auth_permission", "django_content_type"]:
            return 0

        rows = self._parse_sql_tuples(values_text)
        if not rows:
            return 0

        # Handle columns introduced in newer migrations
        if table == "accounts_user":
            if "security_question" not in cols:
                cols.append("security_question")
                for r in rows:
                    r.append("")
            if "security_answer_hash" not in cols:
                cols.append("security_answer_hash")
                for r in rows:
                    r.append("")
        elif table == "content_brand":
            slug_idx = cols.index("slug") if "slug" in cols else None
            img_idx = cols.index("image") if "image" in cols else None
            theme_idx = cols.index("logo_theme") if "logo_theme" in cols else None
            active_idx = cols.index("active") if "active" in cols else None

            if "logo_theme" not in cols:
                cols.append("logo_theme")
                theme_idx = len(cols) - 1
                for r in rows:
                    r.append("light")

            # Known static brand logo mappings to ensure logos are never lost during dump restore
            known_brand_logos = {
                "butane": ("brands/butane.png", "light"),
                "iran-radiator": ("brands/iran-radiator.png", "dark"),
                "chappee": ("brands/chappee.svg", "light"),
                "ariston": ("brands/ariston.svg", "light"),
                "optima": ("brands/optima.png", "light"),
                "lorch": ("brands/lorch.svg", "light"),
                "baxi": ("brands/baxi.svg", "light"),
            }

            for r in rows:
                if slug_idx is not None:
                    slug = str(r[slug_idx])
                    if slug in known_brand_logos:
                        known_img, known_theme = known_brand_logos[slug]
                        if img_idx is not None and not r[img_idx]:
                            r[img_idx] = known_img
                        if theme_idx is not None:
                            r[theme_idx] = known_theme
                        if active_idx is not None:
                            r[active_idx] = 1

        placeholder = "?" if is_sqlite else "%s"
        placeholders = ", ".join([placeholder] * len(cols))
        
        if is_sqlite:
            cols_joined = ", ".join([f'"{c}"' for c in cols])
            sql = f'INSERT INTO "{table}" ({cols_joined}) VALUES ({placeholders})'
        else:
            cols_joined = ", ".join([f"`{c}`" for c in cols])
            sql = f"INSERT INTO `{table}` ({cols_joined}) VALUES ({placeholders})"

        cursor.executemany(sql, rows)
        return len(rows)

    def _parse_sql_tuples(self, values_text):
        text = values_text.strip()
        if text.endswith(";"):
            text = text[:-1].strip()

        rows = []
        i = 0
        n = len(text)

        while i < n:
            while i < n and text[i] != "(":
                i += 1
            if i >= n:
                break

            i += 1  # skip '('
            fields = []
            cur_val = []
            in_str = False
            escape = False

            while i < n:
                c = text[i]
                if escape:
                    if c == "n":
                        cur_val.append("\n")
                    elif c == "r":
                        cur_val.append("\r")
                    elif c == "t":
                        cur_val.append("\t")
                    elif c == "0":
                        cur_val.append("\0")
                    elif c == "'":
                        cur_val.append("'")
                    elif c == '"':
                        cur_val.append('"')
                    elif c == "\\":
                        cur_val.append("\\")
                    else:
                        cur_val.append(c)
                    escape = False
                    i += 1
                    continue
                if c == "\\":
                    escape = True
                    i += 1
                    continue
                if c == "'":
                    in_str = not in_str
                    i += 1
                    continue
                if not in_str:
                    if c == ",":
                        raw_val = "".join(cur_val).strip()
                        fields.append(self._convert_val(raw_val))
                        cur_val = []
                        i += 1
                        continue
                    if c == ")":
                        raw_val = "".join(cur_val).strip()
                        fields.append(self._convert_val(raw_val))
                        cur_val = []
                        i += 1
                        break
                cur_val.append(c)
                i += 1
            rows.append(fields)
        return rows

    def _convert_val(self, raw):
        if raw.upper() == "NULL":
            return None
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            return raw[1:-1]
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw
