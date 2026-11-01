# pylint: disable=invalid-name,unused-import
"""Brands and problems belong directly to a Service (hard FK ownership).

The old design was a reversed M2M on Service (optional per-service curation
with a global fallback). The new design matches the business rule the owner
asked for: a brand or a problem is meaningless without its service, so each
row now carries a mandatory `service` FK and the M2M is removed.

Data migration: existing M2M links are copied to the new FK. Every currently
linked brand/problem is attached to the service that curated it. Brands and
problems that no service curated (the old "global list" items) are attached
to the first service by (sort_order, id) — for the seeded site that is
تعمیر پکیج, which is where those global items came from.
"""
from django.db import migrations, models
import django.db.models.deletion


def forward_copy(apps, schema_editor):
    Brand = apps.get_model("content", "Brand")
    ProblemOption = apps.get_model("content", "ProblemOption")
    Service = apps.get_model("content", "Service")

    services = list(Service.objects.all().order_by("sort_order", "id"))
    if not services:
        return
    default_service = services[0]

    for brand in Brand.objects.all():
        linked = [s for s in services if s.brands.filter(pk=brand.pk).exists()]
        brand.service = linked[0] if linked else default_service
        brand.save(update_fields=["service"])

    for problem in ProblemOption.objects.all():
        linked = [s for s in services if s.problems.filter(pk=problem.pk).exists()]
        problem.service = linked[0] if linked else default_service
        problem.save(update_fields=["service"])


def reverse_clear(apps, schema_editor):
    """Nothing to restore: the M2M can be rebuilt by re-linking every
    brand/problem of each service back onto the service (best effort)."""
    Brand = apps.get_model("content", "Brand")
    ProblemOption = apps.get_model("content", "ProblemOption")
    Service = apps.get_model("content", "Service")

    for service in Service.objects.all():
        service.brands.set(Brand.objects.filter(service=service))
        service.problems.set(ProblemOption.objects.filter(service=service))


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0004_article"),
    ]

    operations = [
        # 1) nullable FK columns
        migrations.AddField(
            model_name="brand",
            name="service",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="brands",
                to="content.service",
                verbose_name="خدمت مربوطه",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="problemoption",
            name="service",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="problems",
                to="content.service",
                verbose_name="خدمت مربوطه",
            ),
            preserve_default=False,
        ),
        # 2) copy the curation data into the ownership FK
        migrations.RunPython(forward_copy, reverse_clear),
        # 3) ownership becomes mandatory
        migrations.AlterField(
            model_name="brand",
            name="service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="brands",
                to="content.service",
                verbose_name="خدمت مربوطه",
            ),
        ),
        migrations.AlterField(
            model_name="problemoption",
            name="service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="problems",
                to="content.service",
                verbose_name="خدمت مربوطه",
            ),
        ),
        # 4) the optional-curation M2M is replaced by hard ownership
        migrations.RemoveField(
            model_name="service",
            name="brands",
        ),
        migrations.RemoveField(
            model_name="service",
            name="problems",
        ),
    ]
