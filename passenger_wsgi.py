"""
Entry point for cPanel's "Setup Python App" (Phusion Passenger).

cPanel runs this file from the "Application root" you choose in the panel.
It loads the .env file next to it, adds the project directory to sys.path,
and exposes the Django `application`.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# PyMySQL ships as the `pymysql` module; Django expects the `MySQLdb` API.
# Installing this shim lets the pure-python driver work on shared hosts
# where the C-extension mysqlclient cannot be compiled.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass  # local/dev installs without PyMySQL keep using SQLite

# Make the project (and the app subdirectory) importable.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load .env so DJANGO_SETTINGS_MODULE, SECRET_KEY, DEBUG, ALLOWED_HOSTS
# etc. are available without shell access.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # python-dotenv is in requirements.txt; keep going if it's missing
    # so a broken install still produces a readable traceback.
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
