from django.urls import path

from .views import flatpage_image_upload

urlpatterns = [
    # upload de imagens do editor de flatpages (TinyMCE, só equipe)
    path("upload-image", flatpage_image_upload, name="opengeosgb_flatpage_image_upload"),
]
