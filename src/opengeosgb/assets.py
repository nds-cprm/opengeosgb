"""
Download de assets locais pelo nginx (X-Accel-Redirect).

No GeoNode 5.0.3, o download de anexos, documentos e arquivos originais de datasets passa pelo
LocalAssetDownloadHandler: o worker do uWSGI lê o arquivo (e, no download, monta um zip na hora) e o
repassa ao cliente. Cada download prende um worker pelo tempo todo, e o harakiri corta os longos.

Aqui, depois de o GeoNode verificar a permissão, o Django só responde com o cabeçalho
X-Accel-Redirect, e o nginx entrega o arquivo direto do volume (sendfile, com Range), sem prender
o worker. Vale para:
- o link (attachment=False): o arquivo pedido, como no GeoNode;
- o download (attachment=True), quando a pasta do asset tem um único arquivo: ele sai como está, e não
  num .zip. Com vários arquivos (ex.: shapefile), o zip continua sendo montado pelo Django.

Só é usado quando a requisição chega pelo nginx, que manda o cabeçalho X-Accel-Assets-Prefix com o
prefixo da rota interna (location internal com alias para ASSETS_ROOT), sempre sobrescrevendo o do
cliente. Direto no uWSGI ou no runserver, sem o cabeçalho, o comportamento é o do GeoNode.
ASSETS_X_ACCEL_REDIRECT=False (settings) desliga.

Registrado em ASSET_HANDLERS/DEFAULT_ASSET_HANDLER e o middleware em MIDDLEWARE (local_settings.py).
"""
import contextvars
import logging
import mimetypes
import os
import re
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from django.utils.http import content_disposition_header

from geonode.assets.local import LocalAssetDownloadHandler, LocalAssetHandler
from geonode.assets.models import LocalAsset

logger = logging.getLogger(__name__)

X_ACCEL_PREFIX_HEADER = "HTTP_X_ACCEL_ASSETS_PREFIX"
# Prefixo da rota interna do nginx, ex.: /_assets_internal/
_VALID_PREFIX = re.compile(r"^/[A-Za-z0-9_\-/]+/$")

_x_accel_prefix = contextvars.ContextVar("opengeosgb_assets_x_accel_prefix", default=None)


class AssetsXAccelMiddleware:
    """Guarda, durante a requisição, o prefixo X-Accel enviado pelo nginx (o handler não recebe o request)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        prefix = request.META.get(X_ACCEL_PREFIX_HEADER, "")
        token = _x_accel_prefix.set(prefix if _VALID_PREFIX.match(prefix) else None)
        try:
            return self.get_response(request)
        finally:
            _x_accel_prefix.reset(token)


def _resolve_local_file(asset, path):
    """O arquivo pedido, com as mesmas regras do GeoNode, ou None (o GeoNode trata o erro)."""
    file0 = asset.location[0]
    if not path:
        return file0 if os.path.isfile(file0) else None
    if os.path.isfile(file0):
        dir0 = os.path.dirname(file0)
    elif os.path.isdir(file0):
        dir0 = file0
    else:
        return None
    localfile = os.path.realpath(os.path.join(dir0, path))
    realassetpath = os.path.realpath(dir0)
    if os.path.commonpath([realassetpath, localfile]) != realassetpath:
        return None
    return localfile if os.path.isfile(localfile) else None


def _single_managed_file(asset):
    """O único arquivo da pasta do asset, ou None se houver vários (ou o asset não for gerenciado)."""
    try:
        managed_dir = LocalAssetHandler._get_managed_dir(asset)
    except ValueError:
        return None
    files = [os.path.join(root, name) for root, _dirs, names in os.walk(managed_dir) for name in names]
    return files[0] if len(files) == 1 else None


class XAccelLocalAssetDownloadHandler(LocalAssetDownloadHandler):

    def create_response(self, asset, attachment=False, basename=None, path=None):
        prefix = _x_accel_prefix.get()
        if not prefix or not getattr(settings, "ASSETS_X_ACCEL_REDIRECT", True):
            return super().create_response(asset, attachment=attachment, basename=basename, path=path)

        real_asset = asset.get_real_instance()
        if not isinstance(real_asset, LocalAsset) or not real_asset.location:
            return super().create_response(asset, attachment=attachment, basename=basename, path=path)

        localfile = _resolve_local_file(real_asset, path)
        if localfile and attachment:
            # o GeoNode zipa a pasta inteira; só um arquivo dispensa o zip
            single = _single_managed_file(real_asset)
            localfile = localfile if single and os.path.realpath(single) == os.path.realpath(localfile) else None
        if not localfile:
            return super().create_response(asset, attachment=attachment, basename=basename, path=path)

        # a rota interna do nginx é um alias de ASSETS_ROOT; fora dele, fica com o GeoNode
        assets_root = os.path.realpath(settings.ASSETS_ROOT)
        realfile = os.path.realpath(localfile)
        if os.path.commonpath([assets_root, realfile]) != assets_root:
            return super().create_response(asset, attachment=attachment, basename=basename, path=path)

        orig_base, ext = os.path.splitext(os.path.basename(localfile))
        outname = f"{basename or orig_base or 'file'}{ext}"
        response = HttpResponse(content_type=mimetypes.guess_type(localfile)[0] or "application/octet-stream")
        response["X-Accel-Redirect"] = prefix + quote(os.path.relpath(realfile, assets_root))
        response["Content-Disposition"] = content_disposition_header(attachment, outname)
        logger.info(f"Asset {real_asset.pk}: '{localfile}' delivered by nginx (X-Accel-Redirect)")
        return response


class XAccelLocalAssetHandler(LocalAssetHandler):

    def get_download_handler(self, asset=None):
        return XAccelLocalAssetDownloadHandler()
