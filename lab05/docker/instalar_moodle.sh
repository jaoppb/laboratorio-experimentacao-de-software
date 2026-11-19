#!/usr/bin/env bash
# Instala as duas instâncias do Moodle por CLI e povoa com dados sintéticos
# (curso de teste, quiz e o usuário estudante aluno_teste_1). Idempotente por serviço.
# Requer: docker compose up -d e docker/.env preenchido.
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a

instalar() {
  local servico="$1" porta="$2" db="$3"
  local exec=(docker compose exec -T -u www-data -e ALUNO_SENHA="$MOODLE_ALUNO_SENHA" "$servico")

  if "${exec[@]}" test -f config.php; then
    echo "$servico: já instalado."
  else
    "${exec[@]}" php admin/cli/install.php \
      --lang=en --wwwroot="http://localhost:$porta" --dataroot=/var/www/moodledata \
      --dbtype=mariadb --dbhost="$db" --dbname=moodle --dbuser=moodle --dbpass="$MYSQL_PASSWORD" \
      --fullname="Lab05 $servico" --shortname="$servico" \
      --adminuser=admin --adminpass="$MOODLE_ADMIN_SENHA" --adminemail=admin@example.invalid \
      --non-interactive --agree-license
  fi

  # Curso sintético, quiz piloto e estudante de teste, iguais nas duas instâncias.
  if "${exec[@]}" php -r 'define("CLI_SCRIPT", true); require "config.php"; exit($DB->record_exists("course", ["shortname" => "lab05"]) ? 0 : 1);'; then
    echo "$servico: curso lab05 já existe."
  else
    # Moodle 5.x move os plugins para public/; 4.5 mantém na raiz.
    local gerador=admin/tool/generator/cli/maketestcourse.php
    "${exec[@]}" test -f "$gerador" || gerador="public/$gerador"
    "${exec[@]}" php "$gerador" --shortname=lab05 --size=XS --bypasscheck
  fi
  "${exec[@]}" php < semear_dados.php
}

instalar moodle45 8045 db45
instalar moodle53 8053 db53
