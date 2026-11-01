"""
WSGI config for the project. Exposes the WSGI callable as `application`.

cPanel's "Setup Python App" uses passenger_wsgi.py instead; this file is
kept for compatibility with other WSGI servers.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
