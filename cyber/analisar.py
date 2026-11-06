"""Entrada única do módulo de Cybersecurity.

    python -m cyber.analisar --alvo api-csharp/src --alvo cyber/exemplos/vulneravel

Para cada alvo: motor PII nos arquivos, taint nos .cs e Índice de Risco Cidadão.
Com a API no ar, o scanner de runtime chama os GETs e o resultado é somado ao alvo
que é um projeto .NET (tem .csproj). Depois, a IA (ou o modo offline) escreve os
alertas e as correções. Saída em cyber/saida/: relatorio.html, achados.json e
fluxos-taint.txt.

Opções:
    --saida PASTA     onde gravar (padrão cyber/saida)
    --api-url URL     onde está a API (padrão http://localhost:5131)
    --sem-runtime     não chama a API
    --offline         não chama a IA, mesmo com chave
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime

from cyber import indice
from cyber.dashboard import gerar as dashboard
from cyber.ia import remediacao
from cyber.pii import regras as pii
from cyber.runtime import scanner
from cyber.taint import analisador as taint

FORMULA = (indice.__doc__ or "").strip()


def _eh_projeto(alvo: str) -> bool:
    for raiz, pastas, nomes in os.walk(alvo):
        pastas[:] = [p for p in pastas if p not in pii.PASTAS_IGNORADAS]
        if any(n.endswith(".csproj") for n in nomes):
            return True
    return False


def _analisar_alvo(alvo: str) -> dict:
    codigo = pii.varrer(alvo, base=".")
    fluxos = taint.analisar(alvo, base=".")
    return {
        "alvo": alvo.replace("\\", "/").rstrip("/"),
        "projeto": _eh_projeto(alvo),
        "fluxos": [f.para_dict() for f in fluxos],
        "achados_codigo_todos": [a.para_dict() for a in codigo.achados],
        "mascarados_codigo": codigo.mascarados,
    }


def _vazamentos(a: dict) -> list[dict]:
    itens = []
    for f in a["fluxos"]:
        if f["status"] == taint.VAZAMENTO:
            itens.append({"chave": ["taint", f["campo"], f["ponto"]], "rotulo": f["rotulo"], "regra": f["regra"],
                          "categoria": f["categoria"], "severidade": f["severidade"], "origem": "taint",
                          "onde": f["tipo_sorvedouro"], "local": f["ponto"],
                          "caminho": " → ".join(f["caminho"])})
    for x in a["achados_codigo_todos"]:
        if x["status"] == pii.ACHADO and x["categoria"] == pii.SEGREDO:
            itens.append({"chave": ["segredo", x["arquivo"], x["linha"]], "rotulo": x["rotulo"], "regra": x["regra"],
                          "categoria": x["categoria"], "severidade": x["severidade"], "origem": "código",
                          "onde": "código", "local": f"{x['arquivo']}:{x['linha']}", "trecho": x["trecho"]})
    rt = a.get("runtime")
    if rt and rt["no_ar"]:
        for x in rt["achados"]:
            if x["status"] == pii.ACHADO:
                itens.append({"chave": ["runtime", x["contexto"].split(" · ")[0].split("?")[0],
                                        x["contexto"].rsplit(" · ", 1)[-1], x["regra"]],
                              "rotulo": x["rotulo"], "regra": x["regra"], "categoria": x["categoria"],
                              "severidade": x["severidade"], "origem": "runtime", "onde": "runtime",
                              "local": x["contexto"], "trecho": x["trecho"]})
    return itens


def _contagens(a: dict, calc: dict) -> None:
    fl = a["fluxos"]
    status = Counter(f["status"] for f in fl)
    codigo = a["achados_codigo_todos"]
    a["achados_codigo"] = codigo
    aceitas_ids = {f["excecao"] for f in fl if f["status"] == taint.EXPOSICAO_ACEITA}
    rt = a.get("runtime") or {}
    a["contagens"] = {
        "vazamentos_unicos": len(calc["parcelas"]),
        "fluxos_vazamento": status[taint.VAZAMENTO],
        "fluxos_sanitizados": status[taint.SANITIZADO],
        "exposicoes_aceitas": len(aceitas_ids),
        "fluxos_aceitos": status[taint.EXPOSICAO_ACEITA],
        "achados_codigo": sum(1 for x in codigo if x["status"] == pii.ACHADO and x["categoria"] != pii.SEGREDO),
        "ficticios": sum(1 for x in codigo if x["status"] == pii.FICTICIO),
        "runtime_vazamentos": sum(1 for x in rt.get("achados", []) if x["status"] == pii.ACHADO),
    }
    por_cat = {c: {"vazamentos": 0, "aceitas": 0, "sanitizados": 0, "codigo": 0, "ficticios": 0} for c in pii.CATEGORIAS}
    for p in calc["parcelas"]:
        por_cat[p["categoria"]]["vazamentos"] += 1
    for f in fl:
        if f["status"] == taint.EXPOSICAO_ACEITA:
            por_cat[f["categoria"]]["aceitas"] += 1
        elif f["status"] == taint.SANITIZADO:
            por_cat[f["categoria"]]["sanitizados"] += 1
    for x in codigo:
        if x["status"] == pii.ACHADO and x["categoria"] != pii.SEGREDO:
            por_cat[x["categoria"]]["codigo"] += 1
        elif x["status"] == pii.FICTICIO:
            por_cat[x["categoria"]]["ficticios"] += 1
    a["por_categoria"] = por_cat


def _itens_para_ia(alvos: list[dict]) -> list[dict]:
    itens = []
    for ai, a in enumerate(alvos):
        pontos_com_saude = {p["local"] for p in a["parcelas"] if p["regra"] == "saude"}
        for n, p in enumerate(a["parcelas"], 1):
            itens.append({"id": f"{ai + 1}.{n}", "alvo": a["alvo"], "regra": p["regra"], "rotulo": p["rotulo"],
                          "categoria": p["categoria"], "onde": p["onde"], "local": p["local"],
                          "caminho": p.get("caminho", ""), "trecho": p.get("trecho", ""),
                          "com_saude": p["local"] in pontos_com_saude})
        n = len(a["parcelas"])
        for x in a["achados_codigo"]:
            if x["status"] == pii.ACHADO and x["categoria"] != pii.SEGREDO:
                n += 1
                itens.append({"id": f"{ai + 1}.{n}", "alvo": a["alvo"], "regra": x["regra"], "rotulo": x["rotulo"],
                              "categoria": x["categoria"], "onde": "código", "local": f"{x['arquivo']}:{x['linha']}",
                              "caminho": "", "trecho": x["trecho"], "com_saude": False})
    return itens


def _texto_fluxos(alvos: list[dict]) -> str:
    linhas = ["Luz Vital · fluxos do taint analysis", ""]
    for a in alvos:
        c = a["contagens"]
        linhas.append(f"== {a['alvo']}  ·  índice {a['indice']} ({a['faixa']})  ·  {c['fluxos_vazamento']} fluxos de "
                      f"vazamento ({c['vazamentos_unicos']} defeitos), {c['fluxos_aceitos']} exposições aceitas, "
                      f"{c['fluxos_sanitizados']} sanitizados")
        for f in a["fluxos"]:
            linhas.append(f"  [{f['status']}] {f['rotulo']} · {f['tipo_sorvedouro']}")
            linhas.append(f"      fonte      {f['fonte']}")
            linhas.append(f"      sorvedouro {f['sorvedouro']}  ({f['chamada']})")
            linhas.append(f"      caminho    {' → '.join(f['caminho'])}")
        linhas.append("")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m cyber.analisar", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alvo", action="append", required=True, help="pasta a analisar (pode repetir)")
    p.add_argument("--saida", default=os.path.join("cyber", "saida"))
    p.add_argument("--api-url", default=scanner.URL_PADRAO)
    p.add_argument("--sem-runtime", action="store_true")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args(argv)

    for alvo in args.alvo:
        if not os.path.isdir(alvo):
            print(f"Alvo não encontrado: {alvo}", file=sys.stderr)
            return 2

    excecoes = taint.carregar_excecoes()
    alvos = [_analisar_alvo(alvo) for alvo in args.alvo]

    if not args.sem_runtime:
        rt = scanner.varrer(args.api_url, excecoes["excecoes"])
        projeto = next((a for a in alvos if a["projeto"]), None)
        rt_dict = {**rt, "achados": [x.para_dict() for x in rt["achados"]]}
        if projeto:
            projeto["runtime"] = rt_dict
        for aviso in rt["avisos"]:
            print(f"[runtime] {aviso}")

    for a in alvos:
        calc = indice.calcular(_vazamentos(a))
        a.update({"indice": calc["indice"], "faixa": calc["faixa"], "soma": calc["soma"], "parcelas": calc["parcelas"]})
        _contagens(a, calc)

    itens = _itens_para_ia(alvos)
    if args.offline:
        rem = remediacao._offline(itens, "opção --offline")
    else:
        rem = remediacao.remediar(itens)

    dados = {
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "comando": "python -m cyber.analisar " + " ".join(f"--alvo {a}" for a in args.alvo),
        "formula": FORMULA,
        "excecoes": excecoes,
        "alvos": [{k: v for k, v in a.items() if k != "achados_codigo_todos"} for a in alvos],
        "remediacao": rem,
    }

    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, "achados.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.saida, "relatorio.html"), "w", encoding="utf-8") as f:
        f.write(dashboard.gerar(dados))
    with open(os.path.join(args.saida, "fluxos-taint.txt"), "w", encoding="utf-8") as f:
        f.write(_texto_fluxos(alvos))

    print()
    print("Luz Vital · Índice de Risco Cidadão")
    for a in alvos:
        c = a["contagens"]
        print(f"  {a['alvo']}")
        print(f"    índice {a['indice']}/100 ({a['faixa']})  ·  vazamentos: {c['vazamentos_unicos']} defeitos em "
              f"{c['fluxos_vazamento']} fluxos  ·  exposições aceitas: {c['exposicoes_aceitas']} "
              f"({c['fluxos_aceitos']} fluxos)  ·  sanitizados: {c['fluxos_sanitizados']}")
        if a.get("runtime"):
            rt = a["runtime"]
            if rt["no_ar"]:
                print(f"    runtime: {len(rt['rotas'])} rotas, {rt['mascarados']} valores mascarados, "
                      f"{c['runtime_vazamentos']} dados inteiros")
    modo = f"online ({rem['modelo']})" if rem["modo"] == "online" else f"offline ({rem['motivo']})"
    print(f"  IA na remediação: {modo}")
    print(f"  Saída: {os.path.join(args.saida, 'relatorio.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
