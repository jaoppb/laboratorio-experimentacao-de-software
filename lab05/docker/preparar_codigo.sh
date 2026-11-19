#!/usr/bin/env bash
# Baixa o código-fonte das tags oficiais do Moodle em docker/codigo/ (ignorado pelo git).
set -euo pipefail

TAG_45="${TAG_45:-v4.5.16}"
TAG_53="${TAG_53:-v5.3.1}"
DESTINO="$(cd "$(dirname "$0")" && pwd)/codigo"

clonar() {
  local tag="$1" pasta="$2"
  if [ -d "$DESTINO/$pasta/.git" ]; then
    echo "$pasta já existe; mantendo."
    return
  fi
  git clone --depth 1 --branch "$tag" https://github.com/moodle/moodle.git "$DESTINO/$pasta"
}

mkdir -p "$DESTINO"
clonar "$TAG_45" moodle-4.5
clonar "$TAG_53" moodle-5.3

# Moodle 5.x exige as dependências do Composer em produção (sem pacotes de desenvolvimento).
# Roda em contêiner para não depender do Composer no host.
for pasta in moodle-4.5 moodle-5.3; do
  if [ -f "$DESTINO/$pasta/composer.json" ] && [ ! -d "$DESTINO/$pasta/vendor" ]; then
    docker run --rm -v "$DESTINO/$pasta:/app" -w /app composer:2 \
      install --no-dev --classmap-authoritative --no-interaction --ignore-platform-reqs
  fi
done
