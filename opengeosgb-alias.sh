#!/bin/bash
# Uso: source opengeosgb-alias.sh  (compatível com bash e zsh)
#
# Define o comando "geonode-docker", que roda o compose do stack usando
# Docker ou Podman. A engine é detectada automaticamente (Docker tem
# prioridade) ou pode ser forçada com a variável CONTAINER_ENGINE:
#   CONTAINER_ENGINE=podman geonode-docker up -d

unalias geonode-docker 2>/dev/null

geonode-docker() {
    local engine="${CONTAINER_ENGINE:-}"
    local -a compose_cmd

    if [ -z "$engine" ]; then
        if command -v docker >/dev/null 2>&1; then
            engine=docker
        elif command -v podman >/dev/null 2>&1; then
            engine=podman
        else
            echo "geonode-docker: nem docker nem podman encontrados no PATH" >&2
            return 1
        fi
    fi

    case "$engine" in
        docker)
            if docker compose version >/dev/null 2>&1; then
                compose_cmd=(docker compose)
            elif command -v docker-compose >/dev/null 2>&1; then
                compose_cmd=(docker-compose)
            else
                echo "geonode-docker: 'docker compose' não está disponível" >&2
                return 1
            fi
            ;;
        podman)
            if podman compose version >/dev/null 2>&1; then
                # suprime o aviso "Executing external compose provider"
                compose_cmd=(env PODMAN_COMPOSE_WARNING_LOGS=false podman compose)
            elif command -v podman-compose >/dev/null 2>&1; then
                compose_cmd=(podman-compose)
            else
                echo "geonode-docker: instale podman-compose ou docker-compose para usar 'podman compose'" >&2
                return 1
            fi
            ;;
        *)
            echo "geonode-docker: CONTAINER_ENGINE inválido '$engine' (use docker ou podman)" >&2
            return 1
            ;;
    esac

    "${compose_cmd[@]}" -f docker-compose.yml -f docker-compose.opengeosgb.yml "$@"
}
