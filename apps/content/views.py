"""Views for CMS content: FAQ, articles and generic pages."""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from apps.content.models import Article, FAQ, Page


def faq(request):
    return render(
        request,
        "faq.html",
        {"faqs": FAQ.objects.filter(active=True)},
    )


def article_list(request):
    articles_qs = Article.objects.filter(published=True).order_by("-created_at")
    paginator = Paginator(articles_qs, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "content/articles.html",
        {
            "articles": page_obj,
            "page_obj": page_obj,
            "total_articles_count": paginator.count,
        },
    )


def article_detail(request, slug):
    article = get_object_or_404(
        Article.objects.select_related("service"), slug=slug, published=True
    )
    more = (
        Article.objects.filter(published=True)
        .exclude(pk=article.pk)
        .order_by("-created_at")[:3]
    )
    return render(
        request,
        "content/article.html",
        {"article": article, "more_articles": more, "band_service": article.service},
    )


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, published=True)
    return render(request, "content/page.html", {"page": page})
