# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path, include
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from geonode.urls import urlpatterns, sitemaps

from . import views
from .metadata.views import RegionsI18nAutocomplete, metadata_page, metadata_page_embed, scales_autocomplete

sitemaps.update(page=FlatPageSitemap)

# Login do admin com recaptcha (mesma flag do login principal)
if settings.RECAPTCHA_ENABLED:
    from .account.forms import AdminReCaptchaAuthenticationForm

    admin.site.login_form = AdminReCaptchaAuthenticationForm
    admin.site.login_template = "admin/login_recaptcha.html"

# Página de visualização de metadados do opengeosgb: inserida no início para ter
# prioridade sobre as rotas de mesmo nome do geonode-mapstore-client
urlpatterns[0:0] = [
    re_path(r"^metadata/(?P<pk>[^/]*)$", metadata_page, name="metadata"),
    re_path(r"^metadata/(?P<pk>[^/]*)/embed$", metadata_page_embed, name="metadata_embed"),
]

urlpatterns += [
    # flatpages
    path("pages/", include("django.contrib.flatpages.urls")),
    # path("about-us/", views.flatpage, {"url": "/about-us/"}, name="about"),

    # Rota legada do GeoNode 4 (P3M)
    re_path(r"^datasets/(?P<layername>[^/]*)/metadata_detail$", views.legacy_metadata_detail, name='dataset_metadata_detail'),

    # Autocomplete de regiões do editor de metadados com nomes traduzidos
    path(
        "opengeosgb/metadata/autocomplete/regions",
        RegionsI18nAutocomplete.as_view(),
        name="opengeosgb_metadata_autocomplete_regions",
    ),
    # Editor de flatpages (app opengeosgb.flatpages_editor): upload de imagens
    path("opengeosgb/flatpages/", include("opengeosgb.flatpages_editor.urls")),

    # Autocomplete do campo de escala (campo esparso do opengeosgb)
    path(
        "opengeosgb/metadata/autocomplete/scales",
        scales_autocomplete,
        name="opengeosgb_metadata_autocomplete_scales",
    ),
]
