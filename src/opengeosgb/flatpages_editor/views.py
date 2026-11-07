import os
import uuid

from PIL import Image
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.flatpages.models import FlatPage
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .editor import IMAGE_FORMATS, MAX_IMAGE_SIZE, TEMP_DIR, UPLOAD_DIR, page_dir


@staff_member_required
@require_POST
def flatpage_image_upload(request):
    """
    Recebe uma imagem do editor de flatpages e devolve {"location": url} (formato do TinyMCE).
    Com ?page=<id>, grava na pasta da página; sem ele (página nova), numa pasta temporária.
    """
    page_id = request.GET.get("page")
    if page_id:
        if not page_id.isdigit() or not FlatPage.objects.filter(pk=page_id).exists():
            return JsonResponse({"error": _("Page not found.")}, status=400)
        directory = page_dir(page_id)
    else:
        directory = f"{UPLOAD_DIR}/{TEMP_DIR}/{uuid.uuid4().hex}"

    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"error": _("No file was sent.")}, status=400)
    if upload.size > MAX_IMAGE_SIZE:
        return JsonResponse({"error": _("The image exceeds the 5 MB limit.")}, status=400)
    try:
        with Image.open(upload) as image:
            image_format = image.format
            image.verify()
    except Exception:
        return JsonResponse({"error": _("The file is not a valid image.")}, status=400)
    if image_format not in IMAGE_FORMATS:
        return JsonResponse({"error": _("Image format not allowed (use PNG, JPEG, GIF or WebP).")}, status=400)

    upload.seek(0)
    # nome original normalizado; a extensão vem do formato validado, não do nome enviado
    base = slugify(os.path.splitext(upload.name or "")[0]) or "imagem"
    name = default_storage.save(f"{directory}/{base}.{IMAGE_FORMATS[image_format]}", upload)
    return JsonResponse({"location": default_storage.url(name)})
