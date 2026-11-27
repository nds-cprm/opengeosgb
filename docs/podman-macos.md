# Podman no macOS

Ajustes necessários além dos já descritos:
- O Podman sem root não publica a porta 80. Libere com `podman machine ssh "sudo sysctl -w net.ipv4.ip_unprivileged_port_start=80"` (vale até a máquina reiniciar).
- O nginx detecta o DNS pelo `/etc/resolv.conf` do container quando `RESOLVER` não está definido no `.env`. Não deixe `RESOLVER=127.0.0.11` no `.env` do Podman: esse endereço só existe no Docker, e as requisições ficam pendentes até dar timeout.
- Se os `apk add` dos builds baseados em Alpine falharem com `DNS: transient error`, o DNS da máquina do Podman travou. Reinicie-a com `podman machine stop && podman machine start` e repita o `sysctl` da porta 80.
- `docker/docker/postgis/initdb-geonode.sh` precisa estar com permissão `755` no host. Com `0700`, o usuário `postgres` não consegue executá-lo, os usuários do GeoNode não são criados e o django falha com `password authentication failed`.
