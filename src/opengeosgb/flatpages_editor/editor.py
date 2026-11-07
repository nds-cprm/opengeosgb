"""
Regras do editor de flatpages: tags permitidas, sanitização do HTML, configuração do TinyMCE
e armazenamento das imagens enviadas.

O editor (TinyMCE 5, embutido no django-tinymce que acompanha o GeoNode) só oferece as tags de
ALLOWED_TAGS, mas a garantia é feita no servidor: o conteúdo é sanitizado ao salvar (admin) e de
novo ao exibir (templates/flatpages/default.html).
"""
import os
import re

import bleach
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.core.files.storage import default_storage
from django.urls import reverse_lazy

# Pasta (dentro de MEDIA_ROOT) das imagens enviadas pelo editor: uma subpasta por página
# (flatpages/<id_da_página>/nome.png). Imagens de páginas ainda não salvas ficam em
# flatpages/tmp/<uuid>/ e são movidas para a pasta da página ao salvá-la (move_temp_images).
UPLOAD_DIR = "flatpages"
TEMP_DIR = "tmp"
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "sub", "sup", "blockquote",
    "h2", "h3", "h4", "ul", "ol", "li", "a", "img",
}
# vale para href e src: endereços data:, javascript: etc. são removidos
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


def _image_src_allowed(value: str) -> bool:
    """Imagens enviadas pelo editor (MEDIA_URL/flatpages/...) ou externas (http/https)."""
    return value.startswith((f"{settings.MEDIA_URL}{UPLOAD_DIR}/", "https://", "http://"))


def _allowed_attribute(tag: str, name: str, value: str) -> bool:
    if tag == "a":
        return name in ("href", "title") or (name == "target" and value == "_blank")
    if tag == "img":
        return name in ("alt", "width", "height") or (name == "src" and _image_src_allowed(value))
    return False


def sanitize_html(html: str) -> str:
    """Remove tudo o que não estiver na lista de tags e atributos permitidos."""
    return bleach.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=_allowed_attribute,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )


# Configuração do TinyMCE só para o campo de conteúdo das flatpages (não altera o padrão global)
TINYMCE_CONFIG = {
    "language": "pt_BR",
    "height": 500,
    "menubar": False,
    "branding": False,
    "plugins": "lists link image paste autolink",
    "toolbar": "undo redo | formatselect | bold italic underline strikethrough | subscript superscript | "
               "bullist numlist blockquote | link image | removeformat",
    "block_formats": "Parágrafo=p; Título 2=h2; Título 3=h3; Título 4=h4",
    # o editor descarta, ao digitar e ao colar, o que estiver fora desta lista (ALLOWED_TAGS)
    "valid_elements": "p,br,strong/b,em/i,u,s,sub,sup,blockquote,h2,h3,h4,ul,ol,li,"
                      "a[href|title|target<_blank],img[src|alt|width|height]",
    "paste_as_text": True,
    "link_target_list": [{"title": "Mesma janela", "value": ""}, {"title": "Nova janela", "value": "_blank"}],
    # upload de imagens (função em static/flatpages_editor/js/image_upload.js, envia o token CSRF);
    # o formulário do admin acrescenta ?page=<id> para páginas já salvas
    "images_upload_url": reverse_lazy("opengeosgb_flatpage_image_upload"),
    "images_upload_handler": "opengeosgbFlatpageImageUpload",
    "automatic_uploads": True,
    "images_file_types": "png,jpg,jpeg,gif,webp",
    "image_dimensions": True,
    "relative_urls": False,
    "remove_script_host": True,
}


def page_dir(page_id) -> str:
    return f"{UPLOAD_DIR}/{page_id}"


def _remove_empty_dir(name: str):
    """Remove uma pasta vazia (o FileSystemStorage não apaga diretórios)."""
    try:
        os.rmdir(default_storage.path(name))
    except (NotImplementedError, OSError):
        pass


def delete_page_images(page_id):
    """Apaga a pasta de imagens da página (flatpages/<id>/) e tudo o que estiver nela."""
    directory = page_dir(page_id)
    try:
        _subdirs, files = default_storage.listdir(directory)
    except (FileNotFoundError, NotImplementedError):
        return
    for name in files:
        default_storage.delete(f"{directory}/{name}")
    _remove_empty_dir(directory)


def move_temp_images(page: FlatPage) -> bool:
    """
    Move para flatpages/<id_da_página>/ as imagens de flatpages/tmp/ usadas no conteúdo da página
    (enviadas antes de a página existir) e corrige os endereços no conteúdo.
    Retorna True se o conteúdo foi alterado.
    """
    temp_url = re.escape(f"{settings.MEDIA_URL}{UPLOAD_DIR}/{TEMP_DIR}/")
    content = page.content
    for url in set(re.findall(temp_url + r"[0-9a-f]{32}/[^\"'\s<>]+", content)):
        old_name = url[len(settings.MEDIA_URL):]
        if not default_storage.exists(old_name):
            continue
        with default_storage.open(old_name) as image:
            new_name = default_storage.save(f"{page_dir(page.pk)}/{os.path.basename(old_name)}", image)
        default_storage.delete(old_name)
        _remove_empty_dir(os.path.dirname(old_name))
        content = content.replace(url, default_storage.url(new_name))
    if content == page.content:
        return False
    page.content = content
    return True
