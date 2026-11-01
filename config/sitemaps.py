"""Sitemap sections for the public site."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.brands.models import Brand
from apps.content.models import Article, Page, ServiceArea
from apps.services.models import Service


class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return [
            "core:home",
            "core:about",
            "core:contact",
            "core:faq",
            "services:list",
            "brands:list",
            "content:articles",
            "requests:start",
        ]

    def location(self, item):
        return reverse(item)


class ServiceSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return Service.objects.filter(active=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class BrandSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return Brand.objects.filter(active=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return Article.objects.filter(published=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class ServiceAreaSitemap(Sitemap):
    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return ServiceArea.objects.filter(active=True, service__active=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class PageSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return Page.objects.filter(published=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViewSitemap,
    "services": ServiceSitemap,
    "areas": ServiceAreaSitemap,
    "brands": BrandSitemap,
    "articles": ArticleSitemap,
    "pages": PageSitemap,
}
