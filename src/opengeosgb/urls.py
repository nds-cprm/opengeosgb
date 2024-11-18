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

from django.urls import path, include
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from geonode.urls import urlpatterns, sitemaps

sitemaps.update(page=FlatPageSitemap)

urlpatterns += [
    # flatpages
    path("pages/", include("django.contrib.flatpages.urls")),
    # path("about-us/", views.flatpage, {"url": "/about-us/"}, name="about"),
]
