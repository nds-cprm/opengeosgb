#!/bin/bash
# Roda o smoke test da imagem base (geonode-base-smoke-test) no build do opengeosgb.
#
# O smoke test exige um "pip check" limpo, mas as versões forçadas em requirements-overrides.txt
# divergem de propósito das fixadas pelo GeoNode ("geonode ... has requirement Pillow==12.1.1, but you
# have pillow 13.0.0."). Este script aceita a falha do "pip check" só quando todas as linhas dele vêm
# dessas versões forçadas. Qualquer outra falha do smoke test, ou do "pip check", faz o build falhar.
#
# Uso: build-smoke-test.sh [opções do geonode-base-smoke-test]

set -u -o pipefail

OVERRIDES="$(dirname "$(readlink -f "$0")")/requirements-overrides.txt"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT

if geonode-base-smoke-test "$@" | tee "$log"; then
    exit 0
fi

# Falhas além do "pip check" não são toleradas
if grep '^FAIL' "$log" | grep -qv '^FAIL  pip check'; then
    exit 1
fi

# pacote==versão forçados, em minúsculas e sem comentários
mapfile -t forced < <(sed -e 's/#.*//' -e 's/[[:space:]]//g' "$OVERRIDES" | grep -v '^$' | tr '[:upper:]' '[:lower:]')

unexpected=0
while IFS= read -r line; do
    lower="${line,,}"
    allowed=0
    for req in "${forced[@]}"; do
        name="${req%%==*}"
        version="${req#*==}"
        if [[ "$lower" == *"but you have $name $version." ]]; then
            allowed=1
            break
        fi
    done
    if [ "$allowed" = 1 ]; then
        echo "aceito (requirements-overrides.txt): $line"
    else
        echo "NÃO aceito: $line"
        unexpected=1
    fi
done < <(/usr/src/venv/bin/pip check)

if [ "$unexpected" = 1 ]; then
    echo "pip check tem divergências que não vêm de requirements-overrides.txt"
    exit 1
fi
echo "smoke test ok, exceto as divergências esperadas de requirements-overrides.txt"
