'use strict';

/**
 * Upload de imagens do TinyMCE (editor de flatpages no admin).
 * Referenciada por nome em flatpages_editor/editor.py (images_upload_handler), pois a configuração
 * do django-tinymce é serializada em JSON. Envia o token CSRF do formulário do admin.
 */
window.opengeosgbFlatpageImageUpload = function (blobInfo, success, failure, progress) {
    const editor = window.tinymce.activeEditor;
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const form = new FormData();
    form.append('file', blobInfo.blob(), blobInfo.filename());

    const xhr = new XMLHttpRequest();
    xhr.open('POST', editor.getParam('images_upload_url'));
    xhr.withCredentials = true;
    if (csrfInput) {
        xhr.setRequestHeader('X-CSRFToken', csrfInput.value);
    }
    xhr.upload.onprogress = function (event) {
        if (progress && event.lengthComputable) {
            progress(event.loaded / event.total * 100);
        }
    };
    xhr.onload = function () {
        let data = {};
        try {
            data = JSON.parse(xhr.responseText);
        } catch (e) {
            // resposta não JSON (ex.: página de login)
        }
        if (xhr.status === 200 && data.location) {
            success(data.location);
        } else {
            failure(data.error || ('HTTP ' + xhr.status), { remove: true });
        }
    };
    xhr.onerror = function () {
        failure('HTTP ' + xhr.status, { remove: true });
    };
    xhr.send(form);
};
