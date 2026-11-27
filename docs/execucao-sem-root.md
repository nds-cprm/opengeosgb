# Execução sem root

`django`, `celery` e `geoserver` rodam com `user: '1000:0'`: UID arbitrário e grupo 0. As imagens dão aos diretórios graváveis a permissão `g=u`, então qualquer UID do grupo 0 consegue gravar neles. Isso também deixa o stack compatível com plataformas que atribuem UIDs aleatórios, como o OpenShift.

Pontos de atenção:
- Scripts copiados para as imagens precisam de permissão de leitura, não só de execução. O `Dockerfile` usa `COPY --chmod=755`, inclusive no `COPY src/`, que exige BuildKit no Docker (padrão nas versões atuais) ou buildah no Podman. Sem isso, a cópia traz as permissões do host (700 num clone feito no macOS) e `manage.py`, o pacote `opengeosgb` e os fixtures ficam `root:root 700`: um UID que não seja o dono, como o aleatório do OpenShift, recebe `Permission denied`. O bind mount de `./src` em desenvolvimento esconde o problema.
- O GeoServer recebe `HOME=/tmp`: no Podman, o `HOME` de um UID sem entrada no `/etc/passwd` seria o `WORKDIR` (`/usr/local/tomcat/tmp`), que não é gravável.
- Volumes criados quando os containers rodavam como root podem ter arquivos que o UID 1000 não consegue gravar. Se aparecer `Permission denied`, ajuste o grupo e as permissões dentro do volume (`chgrp -R 0` e `chmod -R g=u`).
