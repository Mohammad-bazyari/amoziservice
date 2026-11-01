"""Toolbar trimming: which admin change forms need which save buttons.

- «ذخیره و ادامهٔ ویرایش» is only useful when the form has editable inlines
  (after save you stay on the page to keep editing related rows). For plain
  forms it is redundant: «ذخیره» returns to the changelist and re-opening the
  row is one click.
- «ذخیره و ایجاد یکی دیگر» only helps true bulk-entry flows (FAQ, brands,
  problems, articles, pages, SMS templates).

Usage: mix ToolbarMixin into a ModelAdmin.
"""

# Models where "save and add another" genuinely speeds up data entry.
FULL_TOOLBAR_MODELS = {
    "faq",
    "brand",
    "problemoption",
    "article",
    "page",
    "smstemplate",
}


class ToolbarMixin:
    """Trim redundant save buttons in the change-form toolbar."""

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        # An editable inline (e.g. request images/notes) keeps «ذخیره و ادامهٔ
        # ویرایش» meaningful: after saving you stay on the page to continue
        # editing related rows. Plain forms don't need it.
        has_editable_inlines = any(
            inline.has_change_permission or inline.has_add_permission
            for inline in context.get("inline_admin_formsets", [])
        )
        if not has_editable_inlines:
            context["show_save_and_continue"] = False

        model_name = self.model._meta.model_name.lower()
        if model_name not in FULL_TOOLBAR_MODELS:
            context["show_save_and_add_another"] = False

        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)
