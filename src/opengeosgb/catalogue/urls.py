from django.urls import re_path

from . import views

# Incluídas no início do urlpatterns do projeto, para ter prioridade sobre as de
# geonode.catalogue. O reverse("csw_global_dispatch") do núcleo continua dando o
# mesmo endereço.
urlpatterns = [
    re_path(r"^catalogue/csw$", views.csw_global_dispatch, name="opengeosgb_csw"),
]
