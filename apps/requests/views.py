"""Multi-step request wizard (session-backed) + success page.

Steps: service → problem+brand → customer → address → images → review → submit.
Brand is part of the problem step: a select of active brands plus an "other"
option that reveals a free-text brand name. Every step's data is kept in the
wizard session (cookie-based, no database) so users can go back and forward
without losing anything. Uploaded images are held in a per-session temp folder
under MEDIA_ROOT and are attached to the ServiceRequest atomically on submit.
"""
import logging
import mimetypes
import shutil
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.content.models import Brand, ProblemOption, Service
from apps.notifications.services.dispatcher import dispatch_request_notifications
from apps.requests import messages as txt
from apps.requests.forms import (
    StepAddressForm,
    StepCustomerForm,
    StepImagesForm,
    StepProblemForm,
    StepServiceForm,
    validate_image_file,
)
from apps.requests.models import RequestImage, ServiceRequest

logger = logging.getLogger(__name__)

STEPS = ["service", "problem", "customer", "address", "review"]
STEP_FORMS = {
    "service": StepServiceForm,
    "problem": StepProblemForm,
    "customer": StepCustomerForm,
    "address": StepAddressForm,
}
STEP_TITLES = {
    "service": "خدمت",
    "problem": "برند و مشکل",
    "customer": "اطلاعات تماس",
    "address": "آدرس",
    "review": "بازبینی",
}

SESSION_KEY = "request_wizard"
SESSION_IMAGES_KEY = "request_wizard_images"
SESSION_UPLOAD_DIR_KEY = "request_wizard_upload_dir"
SUBMITTED_NONCE_KEY = "request_wizard_submitted"
DUPLICATE_WINDOW_MINUTES = 10


# ---------------------------------------------------------------------------
# session helpers
# ---------------------------------------------------------------------------
def _store(request):
    return request.session.get(SESSION_KEY, {})


def _save_store(request, store):
    request.session[SESSION_KEY] = store


def _step_url(step):
    return reverse("requests:step", kwargs={"step": step})


# ---------------------------------------------------------------------------
# wizard navigation
# ---------------------------------------------------------------------------
def _selected_service(store):
    """The service picked in step 1 (or None) — drives per-step scoping."""
    service_id = (store.get("service") or {}).get("service_choice")
    if service_id:
        return Service.objects.filter(pk=service_id, active=True).first()
    return None


def start(request):
    """Fresh wizard session; optional ?service=<pk> preselects the service
    (used by article CTAs so the user skips re-picking the service)."""
    request.session[SESSION_KEY] = {}
    request.session[SESSION_IMAGES_KEY] = []
    pre = request.GET.get("service")
    if pre and pre.isdigit():
        from apps.content.models import Service as _Service

        if _Service.objects.filter(pk=int(pre), active=True).exists():
            request.session[SESSION_KEY] = {
                "service": {"service_choice": str(int(pre))}
            }
    request.session.modified = True
    store = _store(request)
    if store.get("service"):
        return redirect(_step_url("problem"))
    return redirect(_step_url("service"))


def step_view(request, step):
    if step == "images":
        # Legacy step redirect: images are now uploaded during the problem step
        return redirect("requests:review")

    if step not in STEP_FORMS:  # review is not a form step
        raise Http404(txt.STEP_INVALID)

    # Guard: steps depend on earlier steps being completed.
    required_before = STEPS[: STEPS.index(step)]
    store = _store(request)
    for needed in required_before:
        if not store.get(needed):
            return redirect(_step_url(needed))

    # The problem step is scoped to the service chosen in step 1.
    service = _selected_service(store) if step == "problem" else None

    if request.method == "POST":
        form = STEP_FORMS[step](request.POST, request.FILES, service=service) if step == "problem" else STEP_FORMS[step](request.POST, request.FILES)
    else:
        # Re-entry (back/forward navigation): pre-fill from the session store
        # so previously entered data on every step is kept — no database, the
        # signed cookie session carries it.
        form = STEP_FORMS[step](initial=_store(request).get(step, {}), service=service) if step == "problem" else STEP_FORMS[step](initial=_store(request).get(step, {}))
    step_index = STEPS.index(step)
    step_items = [(s, STEP_TITLES[s]) for s in STEPS]
    prev_step = STEPS[step_index - 1] if step_index > 0 else None
    template_ctx = {
        "form": form,
        "current_step": step,
        "steps": STEPS,
        "step_items": step_items,
        "prev_step": prev_step,
        "current_index": step_index,
        "max_images": settings.REQUEST_IMAGE_MAX_COUNT,
        "max_image_mb": settings.REQUEST_IMAGE_MAX_BYTES // (1024 * 1024),
        "uploaded_images": request.session.get(SESSION_IMAGES_KEY, []),
    }

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        if step == "service":
            _save_store(request, {**store, step: {
                "service_choice": cd.get("service_choice", ""),
            }})
        elif step == "problem":
            saved = _store_uploaded_files(request)
            if saved is None:
                # Files failed validation; re-render the step with errors.
                return render(request, "requests/wizard.html", template_ctx)
            if saved:
                request.session[SESSION_IMAGES_KEY] = (
                    request.session.get(SESSION_IMAGES_KEY, []) + saved
                )
                request.session.modified = True
            _save_store(request, {**store, step: {
                "brand_choice": cd.get("brand_choice", ""),
                "other_brand_name": (cd.get("other_brand_name") or "").strip(),
                "problem_choice": cd.get("problem_choice", ""),
                "other_problem_label": (cd.get("other_problem_label") or "")[:250],
                "description": (cd.get("description") or "")[:2000],
            }})
        else:
            _save_store(request, {**store, step: cd})
        nxt = STEPS[STEPS.index(step) + 1]
        if nxt == "review":  # review is a standalone URL, not a form step
            return redirect("requests:review")
        return redirect(_step_url(nxt))

    return render(request, "requests/wizard.html", template_ctx)


# ---------------------------------------------------------------------------
# uploads
# ---------------------------------------------------------------------------
def _upload_dir(request):
    dir_name = request.session.get(SESSION_UPLOAD_DIR_KEY)
    if not dir_name:
        dir_name = uuid.uuid4().hex
        request.session[SESSION_UPLOAD_DIR_KEY] = dir_name
    path = Path(settings.MEDIA_ROOT) / "tmp" / dir_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _store_uploaded_files(request):
    """Validate uploads, then move them to a per-session temp folder.

    Returns the saved file names, or None when validation fails (the form
    already carries the per-file error messages for re-rendering).
    """
    upload_files = request.FILES.getlist("images")
    saved = []
    if not upload_files:
        return saved

    # Harden here as well as in the form: files arriving outside the normal
    # wizard POST path must never be written to disk unvalidated.
    from django.core.exceptions import ValidationError

    try:
        for f in upload_files:
            validate_image_file(f)
    except ValidationError as exc:
        from django.contrib import messages as _messages

        # نقطه‌ویرگول فارسی؛ در اعلان‌ها و صفحه یک صدا.
        _messages.error(request, txt.MESSAGE_SEPARATOR.join(exc.messages))
        return None
    dest_dir = _upload_dir(request)
    existing = request.session.get(SESSION_IMAGES_KEY, [])
    for f in upload_files:
        if len(existing) + len(saved) >= settings.REQUEST_IMAGE_MAX_COUNT:
            break
        name = f"{uuid.uuid4().hex}{Path(f.name).suffix.lower()}"
        with open(dest_dir / name, "wb+") as out:
            for chunk in f.chunks():
                out.write(chunk)
        saved.append(name)
    return saved


def _cleanup_temp(request):
    dir_name = request.session.get(SESSION_UPLOAD_DIR_KEY)
    if dir_name:
        shutil.rmtree(Path(settings.MEDIA_ROOT) / "tmp" / dir_name, ignore_errors=True)
    request.session.pop(SESSION_UPLOAD_DIR_KEY, None)
    request.session.pop(SESSION_IMAGES_KEY, None)
    request.session.pop(SESSION_KEY, None)
    request.session.pop(SUBMITTED_NONCE_KEY, None)
    request.session.modified = True


# ---------------------------------------------------------------------------
# review + submit
# ---------------------------------------------------------------------------
def _review_context(request):
    """Assemble the review/success data from the session store."""
    store = _store(request)
    service_id = (store.get("service") or {}).get("service_choice")
    problem = store.get("problem") or {}
    brand_id = problem.get("brand_choice")
    problem_id = problem.get("problem_choice")

    service = (
        Service.objects.filter(pk=service_id, active=True).first()
        if service_id
        else None
    )
    if service is None:  # safety net (e.g. service deactivated mid-session)
        service = Service.objects.filter(active=True).order_by("sort_order", "id").first()

    # Brands and problems belong to the service: a session choice referencing
    # an item of another service (or a deactivated one) is dropped here.
    brand = (
        Brand.objects.filter(pk=brand_id, active=True, service=service).first()
        if brand_id and brand_id != "other"
        else None
    )
    problem_obj = (
        ProblemOption.objects.filter(pk=problem_id, active=True, service=service).first()
        if problem_id and problem_id != "other"
        else None
    )

    brand_label = (
        brand.name if brand else problem.get("other_brand_name") or "سایر"
    )
    problem_label = (
        problem_obj.label
        if problem_obj
        else problem.get("other_problem_label") or "سایر"
    )

    customer = store.get("customer") or {}
    address = store.get("address") or {}
    return {
        "service": service,
        "brand": brand,
        "brand_id": brand.pk if brand else None,
        "brand_label": brand_label,
        "problem": problem_obj,
        "problem_id": problem_obj.pk if problem_obj else None,
        "problem_label": problem_label,
        "description": problem.get("description", ""),
        "customer_name": customer.get("customer_name", ""),
        "customer_phone": customer.get("customer_phone", ""),
        "province": address.get("province", "تهران"),
        "city": address.get("city", "تهران"),
        "district": address.get("district", ""),
        "address": address.get("address", ""),
        "plaque": address.get("plaque", ""),
        "unit": address.get("unit", ""),
        "postal_code": address.get("postal_code", ""),
        "address_notes": address.get("address_notes", ""),
        "image_names": request.session.get(SESSION_IMAGES_KEY, []),
    }


def review_view(request):
    review = _review_context(request)
    if not review["service"] or not review["customer_phone"]:
        messages.error(request, txt.INCOMPLETE_REQUEST)
        return redirect("requests:start")
    return render(request, "requests/review.html", {"review": review})


def submit_view(request):
    if request.method != "POST":
        return redirect("requests:review")

    review = _review_context(request)
    if not review["service"] or not review["customer_phone"] or not review["customer_name"]:
        messages.error(request, txt.INCOMPLETE_REQUEST)
        return redirect("requests:start")

    # --- duplicate-submission protection --------------------------------
    window_start = timezone.now() - timedelta(minutes=DUPLICATE_WINDOW_MINUTES)
    duplicate = (
        ServiceRequest.objects.filter(
            customer_phone=review["customer_phone"],
            created_at__gte=window_start,
        )
        .filter(
            Q(brand_id=review["brand_id"]) | Q(other_brand_name__iexact=review["brand_label"])
            if review["brand_id"] is None
            else Q(brand_id=review["brand_id"])
        )
        .first()
    )
    if duplicate:
        _cleanup_temp(request)
        return redirect("requests:success", code=duplicate.tracking_code)

    # Double-submit / refresh guard: one submission per wizard session. The
    # nonce is only committed AFTER the request is created — otherwise a
    # transient failure (DB hiccup) would permanently lock the session with
    # the misleading "already submitted" message and no way to retry.
    if request.session.get(SUBMITTED_NONCE_KEY):
        _cleanup_temp(request)
        messages.info(request, txt.SUBMITTED_BEFORE)
        return redirect("requests:start")

    # --- temp images staged for attachment -------------------------------
    image_names = review["image_names"]
    temp_dir = Path(settings.MEDIA_ROOT) / "tmp" / (request.session.get(SESSION_UPLOAD_DIR_KEY) or "_")
    staged = []
    for name in image_names:
        src = temp_dir / name
        if src.exists():
            staged.append((src, name))

    try:
        with transaction.atomic():
            req = ServiceRequest.objects.create(
                service=review["service"],
                brand=review["brand"],
                other_brand_name="" if review["brand"] else review["brand_label"],
                problem=review["problem"],
                other_problem_label="" if review["problem"] else review["problem_label"],
                description=review["description"],
                customer_name=review["customer_name"],
                customer_phone=review["customer_phone"],
                province=review["province"],
                city=review["city"],
                district=review["district"],
                address=review["address"],
                plaque=review["plaque"],
                unit=review["unit"],
                postal_code="".join(ch for ch in review["postal_code"] if ch.isdigit())[:10],
                address_notes=review["address_notes"],
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            for src, name in staged:
                with open(src, "rb") as fh:
                    django_file = ContentFile(fh.read(), name=name)
                RequestImage.objects.create(
                    request=req,
                    image=django_file,
                    original_filename=name,
                    content_type=mimetypes.guess_type(name)[0] or "",
                    size_bytes=src.stat().st_size,
                )
    except Exception:
        logger.exception("Failed to store service request")
        messages.error(request, txt.SUBMIT_FAILED)
        return redirect("requests:review")

    # Request is committed — mark the session as submitted (refresh guard),
    # then notify the technician AND confirm to the customer. Each leg is
    # independent; SMS failure never affects the stored request (dispatchers
    # swallow all errors).
    request.session[SUBMITTED_NONCE_KEY] = True
    request.session.modified = True
    transaction.on_commit(lambda: dispatch_request_notifications(req))

    _cleanup_temp(request)
    return redirect("requests:success", code=req.tracking_code)


def success_view(request, code):
    req = get_object_or_404(ServiceRequest, tracking_code=code)
    return render(request, "requests/success.html", {"req": req})
