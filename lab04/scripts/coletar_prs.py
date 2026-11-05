"""Coleta o tempo até o merge de PRs do tailwindlabs/tailwindcss, sem e com bot de revisão.

Requer a CLI `gh` autenticada. Usa só a biblioteca padrão.
Saída: dados/reais/pr_merge_time.csv (colunas: repo, pr_number, grupo, tempo_merge_horas, url).

Desenho (ver dados/reais/FONTE.md):
  sem_bot : PRs criados em 2025-01-01..2025-08-31 (antes de qualquer bot de revisão)
  com_bot : PRs criados a partir de 2025-12-01 com comentário/review do coderabbitai antes do merge
  Em ambos: autor humano (User), não-rascunho; amostra aleatória de N por grupo (semente 42).
"""
import csv
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

OWNER, NOME = "tailwindlabs", "tailwindcss"
BOT = "coderabbitai"
N_POR_GRUPO = 30
SEMENTE = 42
SEM_BOT_INICIO, SEM_BOT_FIM = "2025-01-01", "2025-08-31"
COM_BOT_INICIO = "2025-12-01"
PARAR_EM = "2024-12-31"  # para a paginação ao chegar em PRs mais antigos que isso
SAIDA = Path(__file__).resolve().parents[1] / "dados" / "reais" / "pr_merge_time.csv"

CONSULTA = """query($c:String){repository(owner:"%s",name:"%s"){
pullRequests(states:MERGED,first:25,after:$c,orderBy:{field:CREATED_AT,direction:DESC}){
pageInfo{hasNextPage endCursor}
nodes{number url createdAt mergedAt isDraft author{login __typename}
reviews(first:30){nodes{author{login} submittedAt}}
comments(first:30){nodes{author{login} createdAt}}}}}}""" % (OWNER, NOME)


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def buscar():
    cursor, prs = None, []
    while True:
        cmd = ["gh", "api", "graphql", "-f", "query=" + CONSULTA]
        if cursor:
            cmd += ["-f", "c=" + cursor]
        for _ in range(4):  # a API devolve 502 de vez em quando
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                break
            time.sleep(3)
        else:
            sys.exit(f"falha na API do GitHub: {r.stderr[:200]}")
        d = json.loads(r.stdout)["data"]["repository"]["pullRequests"]
        prs += d["nodes"]
        if not d["pageInfo"]["hasNextPage"] or prs[-1]["createdAt"][:10] < PARAR_EM:
            return prs
        cursor = d["pageInfo"]["endCursor"]


def classificar(pr):
    """Devolve 'com_bot', 'sem_bot' ou None (fora do desenho)."""
    if (pr["author"] or {}).get("__typename") != "User" or pr["isDraft"]:
        return None
    criado = pr["createdAt"][:10]
    merge = ts(pr["mergedAt"])
    eventos = pr["reviews"]["nodes"] + pr["comments"]["nodes"]
    bot_antes_do_merge = any(
        e["author"] and e["author"]["login"] == BOT
        and ts(e.get("submittedAt") or e["createdAt"]) < merge
        for e in eventos
    )
    if SEM_BOT_INICIO <= criado <= SEM_BOT_FIM and not bot_antes_do_merge:
        return "sem_bot"
    if criado >= COM_BOT_INICIO and bot_antes_do_merge:
        return "com_bot"
    return None


def main():
    prs = buscar()
    elegiveis = {"com_bot": [], "sem_bot": []}
    for pr in prs:
        g = classificar(pr)
        if g:
            horas = (ts(pr["mergedAt"]) - ts(pr["createdAt"])).total_seconds() / 3600
            elegiveis[g].append((pr["number"], round(horas, 4), pr["url"]))
    rng = random.Random(SEMENTE)
    linhas = []
    for g in ("com_bot", "sem_bot"):
        pool = sorted(elegiveis[g])
        print(f"{g}: {len(pool)} PRs elegíveis")
        for numero, horas, url in sorted(rng.sample(pool, N_POR_GRUPO)):
            linhas.append([f"{OWNER}/{NOME}", numero, g, horas, url])
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["repo", "pr_number", "grupo", "tempo_merge_horas", "url"])
        w.writerows(linhas)
    print(f"{len(linhas)} linhas em {SAIDA}")


if __name__ == "__main__":
    main()
