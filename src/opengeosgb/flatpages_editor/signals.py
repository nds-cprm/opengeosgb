from django.db import transaction

from .editor import delete_page_images


def flatpage_deleted(sender, instance, **kwargs):
    """Sinal post_delete de FlatPage: apaga as imagens só depois de a exclusão ser confirmada no banco."""
    page_id = instance.pk
    transaction.on_commit(lambda: delete_page_images(page_id))
