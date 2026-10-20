#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sincroniza resultados WRF (D:\\dados_wrf\\Resultados_WRF_YYYYMMDD) com o
repositório GitHub Pages (https://rafaelcabralcruz.github.io/WRF/).

v2: espelha APENAS a rodada mais recente (apaga arquivos de rodadas antigas),
    gera index.html e faz push.

Uso:  python sync_wrf.py
"""

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ============================== AJUSTE AQUI ==============================
DADOS = Path(r"D:\dados_wrf")                       # pasta base dos resultados
REPO  = Path(r"D:\WRF")                             # clone local do repositório
REMOTE = "origin"
BRANCH = "main"
# ==========================================================================

VARIAVEIS_CIDADE = ["precip", "temp", "vento"]
ROTULOS_CIDADE = {"precip": "🌧️ Precipitação", "temp": "🌡️ Temperatura", "vento": "💨 Vento"}
VARIAVEIS_MAPA = {
    "Precip": "🌧️ Precipitação",
    "Tmax": "🌡️ Temperatura máxima",
    "Tmean": "🌡️ Temperatura média",
    "Tmin": "🌡️ Temperatura mínima",
    "Wind": "💨 Vento",
}


def rodada_mais_recente(base: Path) -> Path:
    pastas = sorted(p for p in base.glob("Resultados_WRF_*")
                    if re.fullmatch(r"Resultados_WRF_\d{8}", p.name))
    if not pastas:
        raise SystemExit("Nenhuma pasta Resultados_WRF_YYYYMMDD encontrada em " + str(base))
    return pastas[-1]


def rotulo_data(nome: str) -> str:
    """'Precip_20261001.html' -> '01/10/2026'"""
    m = re.search(r"(\d{4})(\d{2})(\d{2})", nome)
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else nome


def espelhar(src: Path, dst_dir: Path) -> list[Path]:
    """Apaga o conteúdo antigo de dst_dir e copia os *.html de src."""
    if not src.exists():
        print(f"AVISO: pasta não encontrada: {src}")
        return []
    dst_dir.mkdir(parents=True, exist_ok=True)
    for antigo in dst_dir.glob("*.html"):
        antigo.unlink()
    copiados = []
    for f in sorted(src.glob("*.html")):
        shutil.copy2(f, dst_dir / f.name)
        copiados.append(f)
    return copiados


def gerar_index(repo: Path, rodada: Path) -> None:
    cidades = {}
    for f in sorted(repo.glob("*.html")):
        if f.name == "index.html":
            continue
        m = re.fullmatch(r"(.+)_(precip|temp|vento)\.html", f.name)
        if m:
            cidades.setdefault(m.group(1), {})[m.group(2)] = f.name

    mapas = {}
    for f in sorted((repo / "mapas").glob("*.html")):
        m = re.fullmatch(r"(Precip|Tmax|Tmean|Tmin|Wind)_(\d{8})\.html", f.name)
        if m:
            mapas.setdefault(m.group(1), []).append(f.name)

    h = ["<!DOCTYPE html>", '<html lang="pt-BR">', "<head>",
         '  <meta charset="UTF-8">',
         "  <title>Previsões WRF — CPTEC/INPE</title>",
         "  <style>",
         "    body { font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }",
         "    h1 { color: #1a5fb4; border-bottom: 2px solid #ddd; padding-bottom: 10px; }",
         "    h2 { color: #444; margin-top: 35px; }",
         "    a { display: inline-block; margin: 4px 12px 4px 0; color: #1a5fb4; text-decoration: none; }",
         "    a:hover { text-decoration: underline; }",
         "    table { border-collapse: collapse; margin-top: 10px; }",
         "    td, th { border: 1px solid #ddd; padding: 6px 14px; text-align: center; }",
         "    th { background: #f2f6fc; }",
         "  </style>", "</head>", "<body>",
         "  <h1>WRF — CPTEC/INPE</h1>",
         f"  <p>Previsão de 7 dias para o Rio Grande do Sul. Rodada de {rotulo_data(rodada.name)}. Escolha a cidade e a variável:</p>"]

    if cidades:
        h.append("  <h2>📍 Previsão por município</h2>")
        for cidade, vars_ in cidades.items():
            h.append(f"  <h2>{cidade.replace('_', ' ')}</h2>")
            for v in VARIAVEIS_CIDADE:
                if v in vars_:
                    h.append(f'  <a href="{vars_[v]}">{ROTULOS_CIDADE[v]}</a>')

    if mapas:
        h.append("  <h2>🗺️ Mapas do estado do RS</h2>")
        for var, rotulo in VARIAVEIS_MAPA.items():
            if var not in mapas:
                continue
            h.append(f"  <h2>{rotulo}</h2>")
            h.append("  <table><tr>" +
                     "".join(f"<th>{rotulo_data(n)}</th>" for n in mapas[var]) +
                     "</tr><tr>" +
                     "".join(f'<td><a href="mapas/{n}">abrir</a></td>' for n in mapas[var]) +
                     "</tr></table>")

    h += ["</body>", "</html>", ""]
    (repo / "index.html").write_text("\n".join(h), encoding="utf-8")


def git(repo: Path, *args) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ERRO no git {' '.join(args)}:\n{r.stderr}")
    return r.stdout


def main() -> None:
    rodada = rodada_mais_recente(DADOS)
    print(f"Rodada: {rodada.name}")

    graficos = rodada / "Graficos_Plotly" / "HTML"
    mapas_src = rodada / "Mapas_Plotly" / "HTML"
    n1 = espelhar(graficos, REPO)
    n2 = espelhar(mapas_src, REPO / "mapas")
    print(f"Gráficos copiados: {len(n1)} | Mapas copiados: {len(n2)}")
    if n2:
        datas = sorted({rotulo_data(f.name) for f in n2})
        print(f"Datas nos mapas: {', '.join(datas)}")

    gerar_index(REPO, rodada)

    git(REPO, "add", "-A")
    status = git(REPO, "status", "--porcelain").strip()
    if not status:
        print("Nada mudou — o conteúdo da nova rodada é idêntico ao do repositório.")
        print("Verifique se os scripts de plotagem geraram arquivos com as datas novas.")
        return
    print("Alterações detectadas:\n" + status)
    git(REPO, "commit", "-m", f"sync {rodada.name} ({datetime.now():%Y-%m-%d %H:%M})")
    git(REPO, "push", REMOTE, BRANCH)
    print("Enviado ao GitHub — site atualiza em ~1 minuto.")


if __name__ == "__main__":
    main()
